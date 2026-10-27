"""Small pooled CNN-LSTM for daily PM2.5, supporting Apple Silicon MPS and CPU.

python train_cnn_lstm.py --device auto --lookback 14 --seeds 11 22 33
Input is read-only. Architecture/settings are fixed before exploratory test scoring.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import sys
import time

ROOT=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.mplconfig'))
import numpy as np
import pandas as pd
try:
    import torch
except ImportError:
    raise SystemExit('PyTorch is missing. Run: python -m pip install -r requirements.txt')
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader,TensorDataset

FEATURES=['pm25','temperature','dew_point','humidity','wind','pressure','rain']
COLUMNS=dict(zip(['Only_Date','Daily Mean PM2.5 Concentration','Temperature','Dew Point',
    'Relative Humidity','Wind Speed','Pressure','Precipitation'],['date',*FEATURES]))
NAMES={'Dekalb':'DeKalb','Etohaw':'Etowah','Jefferson_NB':'Jefferson'}
DEFAULT_WORKBOOK=ROOT.parents[2]/'Meterological_data_ALAbama_copy.xlsx'


def read_workbook(path):
    """Preserve source PM2.5; flag likely weather placeholders in an analysis copy."""
    frames=[]; flags=[]
    for sheet,raw in pd.read_excel(path,sheet_name=None).items():
        absent=set(COLUMNS)-set(raw)
        if absent:raise ValueError(f'{sheet}: required columns absent: {absent}')
        d=raw[list(COLUMNS)].rename(columns=COLUMNS).copy()
        d.date=pd.to_datetime(d.date,errors='raise').dt.normalize()
        if d.date.isna().any() or d.date.duplicated().any():
            raise ValueError(f'{sheet}: missing or duplicate dates')
        for c in FEATURES:
            d[c]=pd.to_numeric(d[c],errors='raise')
        if np.isinf(d[FEATURES]).any().any():raise ValueError(f'{sheet}: infinite values')
        d=d.set_index('date').sort_index()
        d=d.reindex(pd.date_range(d.index.min(),d.index.max()))
        d.index.name='date'
        county=NAMES.get(sheet,sheet)
        zeros=d[['temperature','dew_point','humidity']].eq(0).all(axis=1)
        for c in FEATURES[1:]:
            bad=zeros.copy()
            if c=='pressure':bad|=d[c].le(0)
            if c=='humidity':bad|=d[c].lt(0)|d[c].gt(100)
            if c in ['wind','rain']:bad|=d[c].lt(0)
            for date,value in d.loc[bad & d[c].notna(),c].items():
                flags.append({'county':county,'date':date,'variable':c,'value':value,
                              'action':'analysis_only_set_missing'})
            d.loc[bad,c]=np.nan
        for date,value in d.loc[d.pm25.lt(0),'pm25'].items():
            flags.append({'county':county,'date':date,'variable':'pm25','value':value,
                          'action':'negative_reading_retained'})
        d['county']=county
        frames.append(d.reset_index())
    data=pd.concat(frames,ignore_index=True).sort_values(['county','date']).reset_index(drop=True)
    if data.duplicated(['county','date']).any():raise ValueError('Duplicate mapped county labels')
    return data,pd.DataFrame(flags)


def fit_preprocessing(data,before):
    """County-specific imputation/scaling fitted exclusively on dates < before.

    All-missing features use the pooled TRAINING median. Entirely missing pooled
    columns use zero. Constant features use SD 1. Missingness masks remain inputs.
    Target uses the same mean/SD as historical PM2.5, allowing a persistence skip.
    """
    train=data[data.date.lt(before)]
    global_median=train[FEATURES].median().fillna(0)
    config={'features':FEATURES,'fitted_before':str(pd.Timestamp(before).date()),'counties':{}}
    for county,g in train.groupby('county'):
        if g.pm25.notna().sum()<30:raise ValueError(f'{county}: insufficient training targets')
        median=g[FEATURES].median().fillna(global_median)
        filled=g[FEATURES].fillna(median)
        mean=filled.mean();std=filled.std(ddof=0)
        std=std.where(std.gt(1e-8),1.0)
        config['counties'][county]={'median':median.tolist(),'mean':mean.tolist(),'std':std.tolist()}
    config['county_ids']={c:i for i,c in enumerate(sorted(config['counties']))}
    return config


def calendar_features(date):
    day=date.dayofyear
    return [np.sin(2*np.pi*day/365.25),np.cos(2*np.pi*day/365.25),
            np.sin(4*np.pi*day/365.25),np.cos(4*np.pi*day/365.25),float(date.dayofweek>=5)]


def make_samples(data,preprocess,lookback,forecast_date=None):
    """Each window is county-specific and ends exactly one day before its target.

    Forecast mode accepts a missing future target, but never a missing yesterday
    PM2.5 value. Historical missing predictors use training medians, not future data.
    """
    xs=[];cal=[];ids=[];ys=[];metadata=[]
    for county,g in data.groupby('county'):
        if county not in preprocess['county_ids']:raise ValueError(f'Unknown county {county}')
        g=g.set_index('date').sort_index()
        if forecast_date is not None:
            date=pd.Timestamp(forecast_date)
            g=g.reindex(pd.date_range(g.index.min(),max(date,g.index.max())))
        raw=g[FEATURES].to_numpy(dtype=np.float64)
        p=preprocess['counties'][county]
        missing=np.isnan(raw)
        filled=np.where(missing,np.asarray(p['median']),raw)
        scaled=(filled-np.asarray(p['mean']))/np.asarray(p['std'])
        sequence=np.concatenate([scaled,missing.astype(float)],axis=1).astype(np.float32)
        for i in range(lookback,len(g)):
            date=g.index[i]
            if forecast_date is not None and date!=pd.Timestamp(forecast_date):continue
            if not np.isfinite(raw[i-1,0]):continue
            if forecast_date is None and not np.isfinite(raw[i,0]):continue
            xs.append(sequence[i-lookback:i]);cal.append(calendar_features(date))
            ids.append(preprocess['county_ids'][county])
            ys.append((raw[i,0]-p['mean'][0])/p['std'][0])
            metadata.append({'county':county,'date':date,'window_start':g.index[i-lookback],
                'window_end':g.index[i-1],'observed':raw[i,0],'persistence':raw[i-1,0],
                'target_mean':p['mean'][0],'target_std':p['std'][0]})
    if not xs:raise ValueError('No eligible samples: inspect dates, history length and missing PM2.5')
    arrays=(np.stack(xs),np.asarray(cal,dtype=np.float32),np.asarray(ids,dtype=np.int64),np.asarray(ys,dtype=np.float32))
    return arrays,pd.DataFrame(metadata)


class CNNLSTM(nn.Module):
    """Causal temporal Conv1D -> LSTM -> county/calendar head -> persistence + delta."""
    def __init__(self,n_counties,channels=14,filters=16,hidden=16,dropout=.1):
        super().__init__()
        self.conv=nn.Conv1d(channels,filters,kernel_size=3)
        self.dropout=nn.Dropout(dropout)
        self.lstm=nn.LSTM(filters,hidden,batch_first=True)
        self.county=nn.Embedding(n_counties,4)
        self.head=nn.Sequential(nn.Linear(hidden+4+5,16),nn.ReLU(),nn.Dropout(dropout),nn.Linear(16,1))
        # Start at persistence; the network learns a correction in standardized units.
        nn.init.zeros_(self.head[-1].weight);nn.init.zeros_(self.head[-1].bias)

    def forward(self,x,calendar,county):
        z=x.transpose(1,2)                              # batch, features, days
        z=self.dropout(F.relu(self.conv(F.pad(z,(2,0))))) # left-only causal padding
        z,_=self.lstm(z.transpose(1,2))                 # batch, days, hidden
        delta=self.head(torch.cat([z[:,-1],self.county(county),calendar],dim=1)).squeeze(-1)
        return x[:,-1,0]+delta


def select_device(requested):
    available=torch.backends.mps.is_available()
    if requested=='mps' and not available:
        raise RuntimeError('MPS is unavailable. Use --device cpu; check native arm64 Python, macOS and PyTorch compatibility.')
    device=torch.device('mps' if requested=='mps' or requested=='auto' and available else 'cpu')
    if device.type=='mps':
        # Exercise both forward AND backward before committing to MPS.
        try:
            probe=CNNLSTM(2).to(device)
            probe(torch.zeros(4,7,14,device=device),torch.zeros(4,5,device=device),
                  torch.zeros(4,dtype=torch.long,device=device)).sum().backward()
            torch.mps.synchronize()
        except RuntimeError as error:
            if requested=='mps':raise
            print(f'MPS CNN-LSTM probe failed; using CPU. Reason: {error}',flush=True)
            device=torch.device('cpu')
    return device


def seed_everything(seed):
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    if torch.backends.mps.is_available():torch.mps.manual_seed(seed)


def loader(arrays,mask,batch,shuffle,seed):
    tensors=[torch.from_numpy(np.ascontiguousarray(a[mask])) for a in arrays]
    generator=torch.Generator().manual_seed(seed)
    return DataLoader(TensorDataset(*tensors),batch_size=batch,shuffle=shuffle,
                      num_workers=0,pin_memory=False,generator=generator)


def predict(model,arrays,mask,device,batch=256):
    model.eval();pred=[]
    with torch.no_grad():
        for x,cal,ids,_ in loader(arrays,mask,batch,False,0):
            pred.append(model(x.to(device),cal.to(device),ids.to(device)).cpu().numpy())
    return np.concatenate(pred)


def metrics(y,pred):
    y=np.asarray(y);pred=np.asarray(pred);err=pred-y
    denominator=np.square(y-y.mean()).sum()
    return {'n':len(y),'mae':float(np.abs(err).mean()),'rmse':float(np.sqrt(np.square(err).mean())),
            'bias':float(err.mean()),'r_squared':float(1-np.square(err).sum()/denominator) if denominator>0 else None}


def train(arrays,meta,train_mask,valid_mask,model_config,device,seed,epochs,patience,batch,lr,stage):
    seed_everything(seed)
    model=CNNLSTM(**model_config).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=1e-3)
    loss_function=nn.L1Loss()
    best=float('inf');best_epoch=0;best_state=None;stale=0;history=[]
    batches=loader(arrays,train_mask,batch,True,seed)
    for epoch in range(1,epochs+1):
        model.train();total=0;count=0
        for x,cal,ids,y in batches:
            x,cal,ids,y=(v.to(device) for v in (x,cal,ids,y))
            optimizer.zero_grad(set_to_none=True)
            result=model(x,cal,ids);loss=loss_function(result,y)
            if not torch.isfinite(loss):raise RuntimeError('Nonfinite training loss')
            loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.0);optimizer.step()
            total+=float(loss.detach().cpu())*len(y);count+=len(y)
        row={'seed':seed,'stage':stage,'epoch':epoch,'train_standardized_mae':total/count}
        if valid_mask is not None:
            scaled=predict(model,arrays,valid_mask,device)
            m=meta.loc[valid_mask]
            original=scaled*m.target_std.to_numpy()+m.target_mean.to_numpy()
            score=metrics(m.observed,original)['mae'];row['validation_mae']=score
            if score<best-1e-5:
                best=score;best_epoch=epoch;stale=0
                best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
            else:stale+=1
        history.append(row)
        if epoch==1 or epoch%10==0:
            print(f'seed={seed} {stage} epoch={epoch} training_MAE_z={total/count:.4f}'+
                  (f' validation_MAE={score:.4f}' if valid_mask is not None else ''),flush=True)
        if valid_mask is not None and stale>=patience:break
    if valid_mask is not None:
        model.load_state_dict(best_state)
    else:best_epoch=epochs
    return model,best_epoch,best,history


def write_csv(frame,path):frame.to_csv(path,index=False,float_format='%.17g')


def plots(predictions,history,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(5,2,figsize=(13,15),sharex=True)
    for ax,(county,g) in zip(axes.ravel(),predictions.groupby('county')):
        ax.plot(g.date,g.observed,lw=1,label='Observed')
        ax.plot(g.date,g.prediction,lw=1,label='CNN-LSTM ensemble')
        ax.plot(g.date,g.persistence,lw=.7,alpha=.45,label='Persistence')
        ax.set(title=county,ylabel='PM2.5 (workbook units)');ax.legend(fontsize=6)
    fig.tight_layout();fig.savefig(out/'test_predictions.png',dpi=170,bbox_inches='tight');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4))
    for seed,g in history[history.stage.eq('selection')].groupby('seed'):
        ax.plot(g.epoch,g.validation_mae,label=f'Seed {seed}')
    ax.set(xlabel='Epoch',ylabel='July-September MAE (workbook units)',title='Validation learning curves')
    ax.legend();fig.tight_layout();fig.savefig(out/'validation_curves.png',dpi=170);plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workbook',type=Path,default=DEFAULT_WORKBOOK)
    parser.add_argument('--output',type=Path,default=ROOT/'results')
    parser.add_argument('--device',choices=['auto','cpu','mps'],default='auto')
    parser.add_argument('--lookback',type=int,default=14)
    parser.add_argument('--epochs',type=int,default=80)
    parser.add_argument('--patience',type=int,default=12)
    parser.add_argument('--batch-size',type=int,default=64)
    parser.add_argument('--learning-rate',type=float,default=.001)
    parser.add_argument('--seeds',type=int,nargs='+',default=[11,22,33])
    parser.add_argument('--threads',type=int,default=2)
    args=parser.parse_args()
    if not 3<=args.lookback<=60:parser.error('--lookback must be between 3 and 60')
    if min(args.epochs,args.patience,args.batch_size,args.threads)<=0:parser.error('Counts must be positive')
    if args.learning_rate<=0:parser.error('Learning rate must be positive')
    if len(set(args.seeds))!=len(args.seeds):parser.error('Seeds must be distinct')
    torch.set_num_threads(args.threads)
    device=select_device(args.device)
    print(f'Python architecture={platform.machine()} | torch={torch.__version__} | device={device}',flush=True)
    start=time.perf_counter();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    data,flags=read_workbook(args.workbook)
    if not data.date.dt.year.eq(2025).all():raise ValueError('This experiment uses fixed 2025 date boundaries.')
    write_csv(flags,out/'quality_flags.csv')
    tune_pre=fit_preprocessing(data,'2025-07-01')
    arrays,meta=make_samples(data,tune_pre,args.lookback)
    train_mask=meta.date.lt('2025-07-01').to_numpy()
    valid_mask=meta.date.ge('2025-07-01').to_numpy() & meta.date.lt('2025-10-01').to_numpy()
    if min(train_mask.sum(),valid_mask.sum())<30:raise ValueError('Insufficient train/validation windows')
    final_pre=fit_preprocessing(data,'2025-10-01')
    final_arrays,final_meta=make_samples(data,final_pre,args.lookback)
    refit_mask=final_meta.date.lt('2025-10-01').to_numpy()
    test_mask=final_meta.date.ge('2025-10-01').to_numpy()
    write_csv(meta.assign(split=np.where(train_mask,'selection_train',np.where(valid_mask,'validation','unused_test'))),out/'selection_sample_audit.csv')
    write_csv(final_meta.assign(split=np.where(refit_mask,'refit_train','test')),out/'refit_sample_audit.csv')
    model_config={'n_counties':len(final_pre['county_ids']),'channels':14,'filters':16,'hidden':16,'dropout':.1}
    histories=[];test_predictions=[];seed_scores=[];selection=[]
    for seed in args.seeds:
        _,best_epoch,val_mae,hist=train(arrays,meta,train_mask,valid_mask,model_config,device,
             seed,args.epochs,args.patience,args.batch_size,args.learning_rate,'selection')
        histories+=hist
        print(f'seed={seed}: validation-selected training duration={best_epoch} epochs',flush=True)
        model,_,_,hist=train(final_arrays,final_meta,refit_mask,None,model_config,device,
             seed,best_epoch,args.patience,args.batch_size,args.learning_rate,'refit')
        histories+=hist
        scaled=predict(model,final_arrays,test_mask,device)
        m=final_meta.loc[test_mask].copy()
        pred=scaled*m.target_std.to_numpy()+m.target_mean.to_numpy()
        if not np.isfinite(pred).all():raise RuntimeError('Nonfinite forecasts')
        test_predictions.append(pred)
        seed_scores.append({'seed':seed,**metrics(m.observed,pred)})
        selection.append({'seed':seed,'best_epoch':best_epoch,'validation_mae':val_mae})
        checkpoint={'state_dict':{k:v.detach().cpu() for k,v in model.state_dict().items()},
                    'model_config':model_config,'preprocessing':final_pre,'lookback':args.lookback,
                    'seed':seed,'selected_epochs':best_epoch,'training_end':'2025-09-30',
                    'features':FEATURES,'units':'unverified workbook units'}
        torch.save(checkpoint,out/f'model_seed_{seed}.pt')
        per_seed=m[['county','date','observed','persistence']].copy();per_seed['prediction']=pred
        write_csv(per_seed,out/f'test_predictions_seed_{seed}.csv')
        # Independently reload the serialized model and verify its test predictions.
        loaded=torch.load(out/f'model_seed_{seed}.pt',map_location='cpu',weights_only=True)
        check=CNNLSTM(**loaded['model_config']);check.load_state_dict(loaded['state_dict'])
        check_pred=predict(check,final_arrays,test_mask,torch.device('cpu'))
        if not np.allclose(check_pred,scaled,atol=5e-4,rtol=5e-4):
            raise AssertionError('Checkpoint roundtrip predictions differ beyond CPU/MPS tolerance')
    pred=final_meta.loc[test_mask,['county','date','observed','persistence']].copy()
    pred['prediction']=np.mean(test_predictions,axis=0)
    pred['seed_prediction_sd']=np.std(test_predictions,axis=0,ddof=0)
    write_csv(pred,out/'test_predictions_ensemble.csv')
    write_csv(pd.DataFrame(seed_scores),out/'test_metrics_by_seed.csv')
    write_csv(pd.DataFrame(selection),out/'validation_selected_epochs.csv')
    history=pd.DataFrame(histories);write_csv(history,out/'training_history.csv')
    county_rows=[]
    for county,g in pred.groupby('county'):
        for model,column in [('cnn_lstm_ensemble','prediction'),('persistence','persistence')]:
            county_rows.append({'county':county,'model':model,**metrics(g.observed,g[column])})
    write_csv(pd.DataFrame(county_rows),out/'test_metrics_by_county.csv')
    pooled=[{'model':'cnn_lstm_ensemble',**metrics(pred.observed,pred.prediction)},
            {'model':'persistence',**metrics(pred.observed,pred.persistence)}]
    prior=ROOT.parent/'heldout_daily_predictions.csv'
    comparison_note='Previous study predictions were not found; persistence is the available benchmark.'
    if prior.exists():
        old=pd.read_csv(prior,parse_dates=['date'])
        comparison_note='Prior study predictions compared on exactly the CNN-LSTM test dates.'
        for name,g in old.groupby('model'):
            if name=='persistence':continue
            joined=pred[['county','date','observed']].merge(g,on=['county','date'],suffixes=('_new','_old'),validate='one_to_one')
            if len(joined)!=len(pred):raise ValueError('Prior predictions do not cover all CNN-LSTM dates; use the original workbook or a distinct output folder.')
            if not np.allclose(joined.observed_new,joined.observed_old,atol=1e-8):raise ValueError('Previous study uses different target observations')
            pooled.append({'model':f'previous_{name}',**metrics(joined.observed_new,joined.prediction)})
        selected=old[old.selected_before_test]
        joined=pred[['county','date','observed']].merge(selected,on=['county','date'],suffixes=('_new','_old'),validate='one_to_one')
        if len(joined)!=len(pred):raise ValueError('Previous selected models have different test coverage')
        pooled.append({'model':'previous_validation_selected',**metrics(joined.observed_new,joined.prediction)})
    pooled=pd.DataFrame(pooled);write_csv(pooled,out/'pooled_test_comparison.csv')
    plots(pred,history,out)
    checks={'windows_end_before_target':bool((meta.window_end<meta.date).all()),
            'all_windows_exact_lookback':bool(((meta.window_end-meta.window_start).dt.days+1).eq(args.lookback).all()),
            'no_test_dates_in_refit':bool(final_meta.loc[refit_mask,'date'].lt('2025-10-01').all()),
            'preprocessing_fit_before_test':final_pre['fitted_before']=='2025-10-01',
            'finite_test_predictions':bool(np.isfinite(pred.prediction).all()),
            'checkpoint_reload_predictions_verified':True,
            'county_specific_window_construction':True}
    if not all(checks.values()):raise AssertionError(checks)
    (out/'verification.json').write_text(json.dumps(checks,indent=2))
    metadata={'device':str(device),'architecture':platform.machine(),'python':sys.version,'torch':str(torch.__version__),
        'numpy':np.__version__,'pandas':pd.__version__,'seeds':args.seeds,'lookback':args.lookback,
        'parameters':sum(p.numel() for p in CNNLSTM(**model_config).parameters()),
        'selection_train_windows':int(train_mask.sum()),'validation_windows':int(valid_mask.sum()),
        'refit_windows':int(refit_mask.sum()),'test_windows':int(test_mask.sum()),
        'workbook_sha256':hashlib.sha256(args.workbook.read_bytes()).hexdigest(),
        'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'settings':{'epochs_cap':args.epochs,'patience':args.patience,'batch_size':args.batch_size,'lr':args.learning_rate},
        'elapsed_seconds':time.perf_counter()-start,'comparison_note':comparison_note}
    (out/'run_metadata.json').write_text(json.dumps(metadata,indent=2))
    (out/'preprocessing.json').write_text(json.dumps(final_pre,indent=2))
    baseline=pooled[pooled.model.eq('persistence')].mae.iloc[0]
    error=pooled[pooled.model.eq('cnn_lstm_ensemble')].mae.iloc[0]
    (out/'RESULTS.md').write_text(f'# CNN-LSTM exploratory results\n\nDevice: {device}; parameters: {metadata["parameters"]}; '
        f'lookback: {args.lookback} days; seeds: {args.seeds}.\n\n'
        f'Ensemble test MAE: {error:.4f}; persistence MAE: {baseline:.4f}. '
        f'MAE improvement versus persistence: {(baseline-error)/baseline*100:.2f}%. '
        'A negative improvement means worse forecasts.\n\n'+pooled.to_string(index=False)+'\n\n'
        'Training uses per-county standardized absolute-error loss; validation selects epochs using original-unit pooled MAE. '
        'Each seed refits independently on Jan-Sep for its selected duration. The ensemble averages every specified seed; '
        'no seed is selected using test performance. Seed SD is model variability, not a calibrated prediction interval.\n\n'
        'October-December was already inspected in earlier studies. This is an exploratory comparison, '
        'not a fresh confirmatory test. One year and shared county/weather patterns limit generalization. '
        'Units and reporting delays remain unverified. Forecasts assume yesterday\'s data are available. '
        'Negative readings are retained and predictions are not clipped.\n\n'+comparison_note+'\n')
    print(pooled.to_string(index=False),flush=True)
    print(f'Outputs: {out}',flush=True)


if __name__=='__main__':main()
