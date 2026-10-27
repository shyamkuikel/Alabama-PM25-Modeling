"""Train and compare persistence, ridge, random forest, CNN, LSTM and CNN-LSTM.

All learned families train pooled across counties using the same historical
measurements, calendar information, preprocessing, targets and evaluation dates.
Run: python compare_models.py --device auto
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import itertools
import json
import os
from pathlib import Path
import platform
import time

ROOT=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.mplconfig'))
import joblib
import numpy as np
import pandas as pd
import torch
from torch import nn
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge

from data import (DEFAULT_WORKBOOK,read_workbook,fit_preprocessing,make_samples,
                  metrics,loader,seed_everything,select_device)
from models import (NEURAL_MODELS,ALL_MODELS,ForecastNetwork,classical_inputs,
                    residual_target,classical_predict)


def write_csv(frame,path):frame.to_csv(path,index=False,float_format='%.17g')


def markdown_table(frame):
    rows=[list(frame.columns)]
    for row in frame.itertuples(index=False,name=None):
        rows.append([f'{v:.4f}' if isinstance(v,(float,np.floating)) else str(v) for v in row])
    return '| '+' | '.join(map(str,rows[0]))+' |\n| '+' | '.join(['---']*len(rows[0]))+' |\n'+'\n'.join('| '+' | '.join(row)+' |' for row in rows[1:])


def predict_network(model,arrays,mask,device):
    model.eval();result=[]
    with torch.no_grad():
        for x,cal,county,_ in loader(arrays,mask,256,False,0):
            result.append(model(x.to(device),cal.to(device),county.to(device)).cpu().numpy())
    return np.concatenate(result)


def original_units(scaled,meta):
    return np.asarray(scaled)*meta.target_std.to_numpy()+meta.target_mean.to_numpy()


def train_network(config,arrays,meta,train_mask,valid_mask,device,seed,
                  epochs,patience,batch_size,learning_rate,stage):
    seed_everything(seed)
    model=ForecastNetwork(**config).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=learning_rate,weight_decay=1e-3)
    loss_function=nn.L1Loss()
    batches=loader(arrays,train_mask,batch_size,True,seed)
    best=float('inf');best_epoch=0;best_state=None;stale=0;history=[]
    for epoch in range(1,epochs+1):
        model.train();loss_sum=0;count=0
        for x,cal,county,y in batches:
            x,cal,county,y=(v.to(device) for v in (x,cal,county,y))
            optimizer.zero_grad(set_to_none=True)
            prediction=model(x,cal,county)
            loss=loss_function(prediction,y)
            if not torch.isfinite(loss):raise RuntimeError('Nonfinite training loss')
            loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.0);optimizer.step()
            loss_sum+=float(loss.detach().cpu())*len(y);count+=len(y)
        row={'model':config['architecture'],'width':config['width'],'seed':seed,
             'stage':stage,'epoch':epoch,'training_standardized_mae':loss_sum/count}
        if valid_mask is not None:
            pred=original_units(predict_network(model,arrays,valid_mask,device),meta.loc[valid_mask])
            score=metrics(meta.loc[valid_mask,'observed'],pred)['mae']
            row['validation_mae']=score
            if score<best-1e-5:
                best=score;best_epoch=epoch;stale=0
                best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
            else:stale+=1
        history.append(row)
        if epoch==1 or epoch%10==0:
            print(f'{stage} {config["architecture"]} width={config["width"]} seed={seed} '
                  f'epoch={epoch} train_MAE_z={loss_sum/count:.4f}'+
                  (f' validation_MAE={score:.4f}' if valid_mask is not None else ''),flush=True)
        if valid_mask is not None and stale>=patience:break
    if valid_mask is not None:
        model.load_state_dict(best_state)
    else:best_epoch=epochs
    return model,best_epoch,best,history


def select_neural_width(rows):
    """Select width from average individual-seed validation MAE, never test scores."""
    d=pd.DataFrame(rows)
    scores=d.groupby('width',sort=True).validation_mae.mean()
    return int(scores.idxmin()),float(scores.min())


def uncertainty_table(predictions,replicates=1000,block=7,seed=819):
    """Paired joint-county calendar-block intervals for ensemble MAE differences."""
    p=predictions.copy();p['absolute_error']=(p.prediction-p.observed).abs()
    daily=p.groupby(['date','model']).absolute_error.sum().unstack('model')
    counts=p.groupby(['date','model']).size().unstack('model')
    dates=pd.date_range(p.date.min(),p.date.max())
    daily=daily.reindex(dates,fill_value=0)
    counts=counts.reindex(dates,fill_value=0)
    rng=np.random.default_rng(seed);n=len(dates)
    indices=[]
    for _ in range(replicates):
        starts=rng.integers(0,n,size=int(np.ceil(n/block)))
        indices.append(((starts[:,None]+np.arange(block))%n).ravel()[:n])
    rows=[]
    for a,b in itertools.combinations(sorted(daily.columns),2):
        difference=daily[a].to_numpy()-daily[b].to_numpy()
        denominator=counts[a].to_numpy()
        draws=np.array([difference[ix].sum()/denominator[ix].sum() for ix in indices])
        rows.append({'model_a':a,'model_b':b,'mae_a_minus_b':difference.sum()/denominator.sum(),
                     'ci_low':np.quantile(draws,.025),'ci_high':np.quantile(draws,.975),
                     'bootstrap_replicates':replicates,'block_days':block})
    return pd.DataFrame(rows)


def evaluate(predictions,thresholds):
    rows=[];county_rows=[]
    for model,g in predictions.groupby('model'):
        score={'model':model,**metrics(g.observed,g.prediction)}
        nonnegative=g.observed.ge(0)
        score['mae_nonnegative_targets']=float((g.loc[nonnegative,'prediction']-g.loc[nonnegative,'observed']).abs().mean())
        high=g.observed.ge(g.county.map(thresholds))
        score['high_days_n']=int(high.sum())
        score['high_days_mae']=float((g.loc[high,'prediction']-g.loc[high,'observed']).abs().mean()) if high.any() else np.nan
        rows.append(score)
        for county,cg in g.groupby('county'):
            county_rows.append({'model':model,'county':county,**metrics(cg.observed,cg.prediction)})
    return pd.DataFrame(rows).sort_values('mae'),pd.DataFrame(county_rows)


def plot_results(predictions,pooled,county,history,selected,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    labels={'cnn':'CNN-only','lstm':'LSTM-only','cnn_lstm':'CNN-LSTM','ridge':'Ridge',
            'random_forest':'Random forest','persistence':'Persistence'}
    fig,ax=plt.subplots(figsize=(8,4))
    colors=['#286482' if m!='cnn_lstm' else '#cb7138' for m in pooled.model]
    ax.barh([labels[m] for m in pooled.model],pooled.mae,color=colors)
    for i,v in enumerate(pooled.mae):ax.text(v+.02,i,f'{v:.3f}',va='center')
    ax.invert_yaxis();ax.set(xlabel='October-December MAE (workbook units)',title='Same-data model comparison; lower is better')
    ax.set_xlim(0,pooled.mae.max()*1.15)
    fig.tight_layout();fig.savefig(out/'pooled_mae.png',dpi=180);plt.close(fig)
    pivot=county.pivot(index='county',columns='model',values='mae')
    fig,ax=plt.subplots(figsize=(10,6))
    im=ax.imshow(pivot,aspect='auto',cmap='viridis')
    ax.set_xticks(range(len(pivot.columns)),[labels[m] for m in pivot.columns],rotation=30,ha='right')
    ax.set_yticks(range(len(pivot)),pivot.index);ax.set_title('County MAE on identical dates')
    for i in range(len(pivot)):
        for j in range(len(pivot.columns)):
            v=pivot.iloc[i,j];r,g,b,_=im.cmap(im.norm(v))
            ax.text(j,i,f'{v:.2f}',ha='center',va='center',color='white' if .2126*r+.7152*g+.0722*b<.5 else 'black')
    fig.colorbar(im,ax=ax,label='MAE (workbook units)');fig.tight_layout()
    fig.savefig(out/'county_mae_heatmap.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(14,4),sharey=True)
    for ax,family in zip(axes,NEURAL_MODELS):
        width=selected[family]['width']
        h=history[history.stage.eq('selection') & history.model.eq(family) & history.width.eq(width)]
        for seed,g in h.groupby('seed'):ax.plot(g.epoch,g.validation_mae,label=f'Seed {seed}')
        ax.set(title=f'{labels[family]} (width {width})',xlabel='Epoch',ylabel='Validation MAE')
        ax.legend(fontsize=7)
    fig.tight_layout();fig.savefig(out/'selected_validation_curves.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(5,2,figsize=(14,15),sharex=True)
    for ax,(county,g) in zip(axes.ravel(),predictions.groupby('county')):
        actual=g.drop_duplicates('date').sort_values('date')
        ax.plot(actual.date,actual.observed,color='black',lw=1.2,label='Observed')
        for family in NEURAL_MODELS:
            part=g[g.model.eq(family)].sort_values('date')
            ax.plot(part.date,part.prediction,lw=.85,alpha=.8,label=labels[family])
        ax.set(title=county,ylabel='PM2.5 (workbook units)');ax.legend(fontsize=6,ncol=2)
    fig.tight_layout();fig.savefig(out/'neural_test_forecasts.png',dpi=160,bbox_inches='tight');plt.close(fig)


def create_report(pooled,intervals,seed_metrics,selected,counts,args,device,out):
    hybrid=pooled[pooled.model.eq('cnn_lstm')].iloc[0]
    best=pooled.iloc[0]
    text='# CNN / LSTM / CNN-LSTM and baseline comparison\n\n'
    text+=f'Actual device: {device}. Lookback: {args.lookback} days. Seeds: {args.seeds}. '
    text+='All learned models were newly trained pooled across counties with the same histories, '
    text+='missingness channels, calendar features, county identity and test county-days.\n\n'
    text+='## Pooled test performance\n\n'+markdown_table(pooled[['model','n','mae','rmse','bias','r_squared','high_days_n','high_days_mae']])+'\n\n'
    text+=f'The lowest observed test MAE is {best.mae:.4f} ({best.model}). '
    text+=f'CNN-LSTM MAE is {hybrid.mae:.4f}. This ranking is descriptive; it was not used to select or refit models.\n\n'
    text+='## Does the hybrid add value?\n\n'
    comparisons=[]
    for other in ['cnn','lstm','ridge','random_forest','persistence']:
        baseline=pooled[pooled.model.eq(other)].mae.iloc[0]
        row=intervals[((intervals.model_a.eq('cnn_lstm')) & intervals.model_b.eq(other)) |
                      ((intervals.model_b.eq('cnn_lstm')) & intervals.model_a.eq(other))].iloc[0]
        sign=1 if row.model_a=='cnn_lstm' else -1
        lo,hi=(row.ci_low,row.ci_high) if sign==1 else (-row.ci_high,-row.ci_low)
        comparisons.append({'comparison':f'CNN-LSTM minus {other}','mae_difference':hybrid.mae-baseline,
                            'ci_low':lo,'ci_high':hi,'mae_improvement_percent':100*(baseline-hybrid.mae)/baseline})
    text+=markdown_table(pd.DataFrame(comparisons))+'\n\n'
    text+='Negative MAE differences favor CNN-LSTM. Intervals use paired seven-day calendar-block '
    text+='resampling with all counties resampled together. They are exploratory pointwise intervals, '
    text+='not simultaneous multiple-comparison intervals, and condition on the fitted ensembles. '
    text+='An interval crossing zero does not clearly distinguish the models. It does not establish equality.\n\n'
    text+='## Single-run variability\n\n'+markdown_table(seed_metrics)+'\n\n'
    text+='Primary CNN, LSTM, CNN-LSTM and random-forest predictions average ALL declared seeds; '
    text+='ridge and persistence are deterministic. Per-seed metrics also allow single-model comparisons '
    text+='without crediting only neural networks for ensembling. Across-seed SD is not a prediction interval.\n\n'
    text+='## Design\n\n'
    text+=f'Selection training: Jan-Jun ({counts["selection_train"]} windows); validation: Jul-Sep '
    text+=f'({counts["validation"]}); refit training: Jan-Sep ({counts["refit"]}); test: Oct-Dec '
    text+=f'({counts["test"]}). Each sequence stays within one county and ends the day before its target. '
    text+='Preprocessing fits Jan-Jun for selection and Jan-Sep for refitting. Missing targets and '
    text+='missing yesterday PM2.5 are excluded; older missing inputs are training-median imputed with masks. '
    text+='No future interpolation or test fitting is used.\n\n'
    text+='All five learned families predict a correction to persistence in county-standardized units. '
    text+='CNN-only reads all encoded days through a flattened projection; LSTM-only reads the same full '
    text+='sequence; CNN-LSTM convolves then recurs. Neural heads share county embedding, calendar, '
    text+='dropout, optimizer, loss and persistence skip. Ridge and forest flatten the same history and '
    text+='receive one-hot county identity. Parameter counts differ and are reported.\n\n'
    text+='Neural width is selected by mean individual-seed validation MAE; each seed gets a '
    text+='validation-selected epoch count. Ridge alpha and forest depth/leaf size are selected with '
    text+='the same validation dates and original-unit MAE criterion. Candidate budgets differ and '
    text+='are explicit in validation_scores.csv. Neural training uses standardized L1 loss; ridge '
    text+='and forest use squared-error fitting, so comparisons do not isolate architecture alone. '
    text+='All families refit with chosen settings before test scoring.\n\n'
    text+='## Limits\n\n'
    text+='Oct-Dec has already been inspected in earlier analyses, so this is not a fresh confirmatory '
    text+='test. One year, overlapping windows, shared weather inputs and correlated counties limit '
    text+='generalization. More years are needed. Units and reporting delays are unverified. '
    text+='Training-period county 95th percentiles define high days; some test subsets can be small. '
    text+='Negative readings remain in the primary analysis and forecasts are not clipped. '
    text+='The nonnegative-target metric is an evaluation sensitivity, not a retraining. '
    text+='MPS acceleration is used only when available; see metadata for the actual device.\n\n'
    text+='## Selected settings\n\n```json\n'+json.dumps(selected,indent=2)+'\n```\n'
    (out/'REPORT.md').write_text(text,encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workbook',type=Path,default=DEFAULT_WORKBOOK)
    parser.add_argument('--output',type=Path,default=ROOT/'results')
    parser.add_argument('--device',choices=['auto','cpu','mps'],default='auto')
    parser.add_argument('--lookback',type=int,default=14)
    parser.add_argument('--seeds',nargs='+',type=int,default=[11,22,33])
    parser.add_argument('--widths',nargs='+',type=int,default=[8,16])
    parser.add_argument('--epochs',type=int,default=80)
    parser.add_argument('--patience',type=int,default=12)
    parser.add_argument('--batch-size',type=int,default=64)
    parser.add_argument('--learning-rate',type=float,default=.001)
    parser.add_argument('--rf-trees',type=int,default=150)
    parser.add_argument('--bootstrap',type=int,default=1000)
    parser.add_argument('--threads',type=int,default=2)
    args=parser.parse_args()
    if not 3<=args.lookback<=60:parser.error('Lookback must be 3..60')
    if min(args.epochs,args.patience,args.batch_size,args.rf_trees,args.threads,*args.widths)<=0:parser.error('Counts must be positive')
    if args.bootstrap<20 or args.learning_rate<=0:parser.error('Use bootstrap >=20 and a positive learning rate')
    if len(set(args.seeds))!=len(args.seeds) or len(set(args.widths))!=len(args.widths):parser.error('Seeds and widths must be distinct')
    started=time.perf_counter();torch.set_num_threads(args.threads)
    device=select_device(args.device)
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    model_dir=out/'models';model_dir.mkdir(exist_ok=True)
    input_hash=hashlib.sha256(args.workbook.read_bytes()).hexdigest()
    print(f'Architecture={platform.machine()} device={device} torch={torch.__version__}',flush=True)
    data,flags=read_workbook(args.workbook)
    if not data.date.dt.year.eq(2025).all():raise ValueError('This configured experiment requires 2025 observations.')
    write_csv(flags,out/'quality_flags.csv')
    tune_pre=fit_preprocessing(data,'2025-07-01')
    arr,meta=make_samples(data,tune_pre,args.lookback)
    train_mask=meta.date.lt('2025-07-01').to_numpy()
    val_mask=(meta.date.ge('2025-07-01') & meta.date.lt('2025-10-01')).to_numpy()
    final_pre=fit_preprocessing(data,'2025-10-01')
    final,final_meta=make_samples(data,final_pre,args.lookback)
    refit_mask=final_meta.date.lt('2025-10-01').to_numpy()
    test_mask=final_meta.date.ge('2025-10-01').to_numpy()
    if min(train_mask.sum(),val_mask.sum(),refit_mask.sum(),test_mask.sum())<30:raise ValueError('Insufficient windows')
    n_counties=len(final_pre['county_ids'])
    counts={'selection_train':int(train_mask.sum()),'validation':int(val_mask.sum()),
            'refit':int(refit_mask.sum()),'test':int(test_mask.sum())}
    write_csv(meta.assign(split=np.where(train_mask,'train',np.where(val_mask,'validation','not_used'))),out/'selection_sample_audit.csv')
    write_csv(final_meta.assign(split=np.where(refit_mask,'refit','test')),out/'final_sample_audit.csv')
    (out/'preprocessing_selection.json').write_text(json.dumps(tune_pre,indent=2))
    (out/'preprocessing_final.json').write_text(json.dumps(final_pre,indent=2))
    threshold=data[data.date.lt('2025-10-01')].groupby('county').pm25.quantile(.95)
    write_csv(threshold.rename('training_p95').reset_index(),out/'training_high_day_thresholds.csv')
    selected={};validation=[];history=[];manifest=[];seed_predictions={};parameter_rows=[]
    # Select ALL settings before producing any test predictions.
    for family in NEURAL_MODELS:
        family_rows=[]
        for width in args.widths:
            config={'architecture':family,'n_counties':n_counties,'lookback':args.lookback,
                    'width':width,'channels':14,'dropout':.1}
            parameter_rows.append({'model':family,'width':width,'parameters':sum(p.numel() for p in ForecastNetwork(**config).parameters())})
            for seed in args.seeds:
                t=time.perf_counter()
                _,epoch,val,hist=train_network(config,arr,meta,train_mask,val_mask,device,
                    seed,args.epochs,args.patience,args.batch_size,args.learning_rate,'selection')
                history+=hist
                row={'model':family,'width':width,'seed':seed,'best_epoch':epoch,
                     'validation_mae':val,'seconds':time.perf_counter()-t}
                validation.append(row);family_rows.append(row)
        width,score=select_neural_width(family_rows)
        selected[family]={'width':width,'mean_validation_mae':score,
                         'epochs_by_seed':{str(r['seed']):int(r['best_epoch']) for r in family_rows if r['width']==width}}
        print(f'Selected {family}: width={width}, validation_MAE={score:.4f}',flush=True)
    x=classical_inputs(arr,n_counties);residual=residual_target(arr)
    ridge_rows=[]
    for alpha in [1.,10.,100.,1000.]:
        model=Ridge(alpha=alpha).fit(x[train_mask],residual[train_mask])
        p=original_units(classical_predict(model,arr,n_counties,val_mask),meta.loc[val_mask])
        score=metrics(meta.loc[val_mask,'observed'],p)['mae']
        row={'model':'ridge','alpha':alpha,'validation_mae':score}
        validation.append(row);ridge_rows.append(row)
    choice=min(ridge_rows,key=lambda r:r['validation_mae'])
    selected['ridge']={'alpha':choice['alpha'],'validation_mae':choice['validation_mae']}
    forest_rows=[]
    for depth,leaf in itertools.product([6,None],[5,15]):
        config={'n_estimators':args.rf_trees,'max_depth':depth,'min_samples_leaf':leaf,
                'max_features':.7,'criterion':'squared_error','n_jobs':args.threads}
        seed_rows=[]
        for seed in args.seeds:
            model=RandomForestRegressor(**config,random_state=seed).fit(x[train_mask],residual[train_mask])
            p=original_units(classical_predict(model,arr,n_counties,val_mask),meta.loc[val_mask])
            score=metrics(meta.loc[val_mask,'observed'],p)['mae']
            row={'model':'random_forest','seed':seed,'max_depth':depth,'min_samples_leaf':leaf,'validation_mae':score}
            validation.append(row);seed_rows.append(row)
        forest_rows.append({'config':config,'mean_validation_mae':float(np.mean([r['validation_mae'] for r in seed_rows]))})
    selected['random_forest']=min(forest_rows,key=lambda r:r['mean_validation_mae'])
    # Persist a test-independent record of all selected settings before final fitting.
    (out/'selected_settings.json').write_text(json.dumps(selected,indent=2))
    write_csv(pd.DataFrame(validation),out/'validation_scores.csv')
    write_csv(pd.DataFrame(parameter_rows),out/'neural_parameter_counts.csv')
    print('All settings selected. Refit on Jan-Sep; score Oct-Dec only after fitting.',flush=True)
    test_meta=final_meta.loc[test_mask].copy()
    for family in NEURAL_MODELS:
        config={'architecture':family,'n_counties':n_counties,'lookback':args.lookback,
                'width':selected[family]['width'],'channels':14,'dropout':.1}
        seed_predictions[family]={}
        for seed in args.seeds:
            epochs=selected[family]['epochs_by_seed'][str(seed)]
            model,_,_,hist=train_network(config,final,final_meta,refit_mask,None,device,
                seed,epochs,args.patience,args.batch_size,args.learning_rate,'refit')
            history+=hist
            scaled=predict_network(model,final,test_mask,device)
            seed_predictions[family][seed]=original_units(scaled,test_meta)
            name=f'{family}_seed_{seed}.pt'
            checkpoint={'state_dict':{k:v.detach().cpu() for k,v in model.state_dict().items()},
                        'model_config':config,'seed':seed,'epochs':epochs,'training_end':'2025-09-30'}
            torch.save(checkpoint,model_dir/name)
            manifest.append({'family':family,'seed':seed,'file':f'models/{name}','format':'torch_state_dict'})
            loaded=torch.load(model_dir/name,map_location='cpu',weights_only=True)
            reloaded=ForecastNetwork(**loaded['model_config']);reloaded.load_state_dict(loaded['state_dict'])
            actual=predict_network(reloaded,final,test_mask,torch.device('cpu'))
            if not np.allclose(actual,scaled,atol=5e-4,rtol=5e-4):raise AssertionError('Neural checkpoint roundtrip')
    final_x=classical_inputs(final,n_counties);final_residual=residual_target(final)
    ridge=Ridge(alpha=selected['ridge']['alpha']).fit(final_x[refit_mask],final_residual[refit_mask])
    joblib.dump(ridge,model_dir/'ridge.joblib')
    manifest.append({'family':'ridge','file':'models/ridge.joblib','format':'joblib'})
    ridge_prediction=original_units(classical_predict(ridge,final,n_counties,test_mask),test_meta)
    seed_predictions['random_forest']={}
    for seed in args.seeds:
        forest=RandomForestRegressor(**selected['random_forest']['config'],random_state=seed).fit(final_x[refit_mask],final_residual[refit_mask])
        name=f'forest_seed_{seed}.joblib';joblib.dump(forest,model_dir/name)
        manifest.append({'family':'random_forest','seed':seed,'file':f'models/{name}','format':'joblib'})
        scaled=classical_predict(forest,final,n_counties,test_mask)
        seed_predictions['random_forest'][seed]=original_units(scaled,test_meta)
        reloaded=joblib.load(model_dir/name)
        if not np.allclose(classical_predict(reloaded,final,n_counties,test_mask),scaled):raise AssertionError('Forest checkpoint roundtrip')
    ensembles={'persistence':test_meta.persistence.to_numpy(),'ridge':ridge_prediction}
    seed_rows=[];long_seed_predictions=[]
    for family,seed_map in seed_predictions.items():
        ensembles[family]=np.mean(list(seed_map.values()),axis=0)
        for seed,pred in seed_map.items():
            seed_rows.append({'model':family,'seed':seed,**metrics(test_meta.observed,pred)})
            frame=test_meta[['county','date','observed']].copy()
            frame['model']=family;frame['seed']=seed;frame['prediction']=pred
            long_seed_predictions.append(frame)
    predictions=[]
    for family in ALL_MODELS:
        part=test_meta[['county','date','observed','persistence']].copy()
        part['model']=family;part['prediction']=ensembles[family]
        if family in seed_predictions:
            part['seed_prediction_sd']=np.std(list(seed_predictions[family].values()),axis=0,ddof=0)
        else:part['seed_prediction_sd']=0.
        predictions.append(part)
    predictions=pd.concat(predictions,ignore_index=True)
    if not np.isfinite(predictions.prediction).all():raise AssertionError('Nonfinite prediction')
    pooled,county=evaluate(predictions,threshold)
    intervals=uncertainty_table(predictions,args.bootstrap)
    seed_metrics=pd.DataFrame(seed_rows)
    paired=[]
    seed_pivot=seed_metrics.pivot(index='seed',columns='model',values='mae')
    for other in ['cnn','lstm','random_forest']:
        differences=seed_pivot.cnn_lstm-seed_pivot[other]
        for seed,value in differences.items():paired.append({'seed':seed,'comparison':f'cnn_lstm_minus_{other}','mae_difference':value})
    history=pd.DataFrame(history)
    write_csv(predictions,out/'test_predictions.csv')
    write_csv(pd.concat(long_seed_predictions),out/'test_predictions_by_seed.csv')
    write_csv(pooled,out/'pooled_test_metrics.csv')
    write_csv(county,out/'county_test_metrics.csv')
    write_csv(seed_metrics,out/'seed_test_metrics.csv')
    write_csv(pd.DataFrame(paired),out/'paired_seed_mae_differences.csv')
    write_csv(intervals,out/'paired_model_mae_intervals.csv')
    write_csv(history,out/'training_history.csv')
    (out/'model_manifest.json').write_text(json.dumps(manifest,indent=2))
    metadata={'device':str(device),'architecture':platform.machine(),'lookback':args.lookback,'seeds':args.seeds,
        'width_candidates':args.widths,'counts':counts,'elapsed_seconds':time.perf_counter()-started,
        'settings':vars(args).copy(),'input_sha256':input_hash,
        'code_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'models.py',ROOT/'data.py',ROOT.parent/'cnn_lstm/train_cnn_lstm.py']},
        'versions':{p:importlib.metadata.version(p) for p in ['torch','numpy','pandas','openpyxl','scikit-learn','joblib','matplotlib']},
        'test_status':'exploratory: October-December outcomes were inspected in previous studies',
        'primary_prediction':'mean of all prespecified seeds per stochastic model family',
        'units':'unverified workbook units'}
    metadata['settings']['workbook']=str(args.workbook.resolve());metadata['settings']['output']=str(out)
    (out/'run_metadata.json').write_text(json.dumps(metadata,indent=2))
    verify={'source_unchanged':input_hash==hashlib.sha256(args.workbook.read_bytes()).hexdigest(),
        'preprocessing_selection_ends_before_july':tune_pre['fitted_before']=='2025-07-01',
        'preprocessing_refit_ends_before_october':final_pre['fitted_before']=='2025-10-01',
        'all_windows_end_day_before_target':bool(final_meta.window_end.eq(final_meta.date-pd.Timedelta(days=1)).all()),
        'all_families_same_test_dates':all(g.groupby('model').date.apply(lambda s:tuple(s)).nunique()==1 for _,g in predictions.groupby('county')),
        'six_model_families':set(predictions.model)==set(ALL_MODELS),
        'all_predictions_finite':bool(np.isfinite(predictions.prediction).all()),
        'neural_and_forest_reload_verified':True}
    if not all(verify.values()):raise AssertionError(verify)
    (out/'verification.json').write_text(json.dumps(verify,indent=2))
    plot_results(predictions,pooled,county,history,selected,out)
    create_report(pooled,intervals,seed_metrics,selected,counts,args,device,out)
    print(pooled.to_string(index=False),flush=True)
    print('Saved complete comparison:',out,flush=True)


if __name__=='__main__':main()
