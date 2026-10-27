"""Three-fold chronological tuning, frozen refit and six-model pooled comparison."""
import argparse,hashlib,importlib,importlib.metadata,json,os,platform,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.mplconfig'))
import joblib
import numpy as np
import pandas as pd
import torch
from prepare_data import prepare,DEFAULT_WORKBOOK
from preprocessing import fit_preprocessing,make_samples,predict,metrics
from splits import FOLDS,TEST_START,masks,stopping_start
from training import fit_neural,units,design,residual,classical_predict,select_device
FAMILIES=['persistence','ridge','random_forest','cnn','lstm','cnn_lstm']


def save_json(obj,path):Path(path).write_text(json.dumps(obj,indent=2))
def save_csv(frame,path):frame.to_csv(path,index=False,float_format='%.17g')


def build_context(data,lookback,train_end,valid_end):
    pre=fit_preprocessing(data,train_end)
    arrays,meta=make_samples(data,pre,lookback)
    train,valid=masks(meta,train_end,valid_end)
    if not train.any() or not valid.any():raise ValueError('Empty fold')
    assert meta.loc[train,'date'].max()<meta.loc[valid,'date'].min()
    assert (meta.window_end==meta.date-pd.Timedelta(days=1)).all()
    return {'pre':pre,'arrays':arrays,'meta':meta,'train':train,'valid':valid,'n_counties':len(pre['county_ids'])}


def main(forced_models=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workbook',type=Path,default=DEFAULT_WORKBOOK)
    parser.add_argument('--data',type=Path,default=ROOT/'data/merged_clean.csv')
    parser.add_argument('--output',type=Path,default=ROOT/('results' if forced_models is None else f'results_single/{forced_models[0]}'))
    parser.add_argument('--models',nargs='+',choices=FAMILIES,default=forced_models or FAMILIES)
    parser.add_argument('--device',choices=['auto','cpu','mps'],default='auto')
    parser.add_argument('--seeds',nargs='+',type=int,default=[11,22,33])
    parser.add_argument('--lookback',type=int,default=14)
    parser.add_argument('--epochs',type=int,default=60)
    parser.add_argument('--patience',type=int,default=8)
    parser.add_argument('--batch-size',type=int,default=64)
    parser.add_argument('--trees',type=int,default=150)
    parser.add_argument('--threads',type=int,default=2)
    parser.add_argument('--bootstrap',type=int,default=1000)
    parser.add_argument('--smoke',action='store_true',help='One candidate, one seed, two epochs and 20 trees; separate output required.')
    args=parser.parse_args()
    if min(args.epochs,args.patience,args.batch_size,args.trees,args.threads)<=0 or not 3<=args.lookback<=60:parser.error('Invalid positive count/history length')
    if len(set(args.seeds))!=len(args.seeds) or len(set(args.models))!=len(args.models):parser.error('Duplicate seeds/models')
    if args.bootstrap<20:parser.error('At least 20 bootstrap replicates')
    if args.smoke:
        if args.output==ROOT/'results':parser.error('Set --output to a separate smoke directory')
        args.seeds=args.seeds[:1];args.epochs=2;args.trees=20;args.bootstrap=50
    start=time.perf_counter();torch.set_num_threads(args.threads);device=select_device(args.device)
    out=args.output.resolve()
    if (out/'selected_settings.json').exists():parser.error('Output already contains a run. Choose another --output directory.')
    out.mkdir(parents=True,exist_ok=True);(out/'models').mkdir(exist_ok=True)
    if not args.data.exists():prepare(args.workbook,args.data.parent)
    data=(pd.read_excel(args.data,sheet_name='Clean panel') if args.data.suffix.lower()=='.xlsx'
          else pd.read_csv(args.data,parse_dates=['date']))
    data['date']=pd.to_datetime(data.date).dt.normalize()
    if data.duplicated(['county','date']).any():raise ValueError('Duplicate county/date')
    if not data.date.dt.year.eq(2025).all():raise ValueError('Configured folds require 2025 data')
    if np.isinf(data.select_dtypes('number')).any().any():raise ValueError('Infinite input')
    contexts={};fold_audits=[];history=[];cv_rows=[];seed_rows=[];cv_predictions=[];epochs_lookup={}
    for fold,train_end,valid_end in FOLDS:
        context=build_context(data,args.lookback,train_end,valid_end)
        inner_start=stopping_start(train_end)
        context['inner']=build_context(data,args.lookback,inner_start,train_end)
        contexts[fold]=context
        save_json(context['pre'],out/f'preprocessing_{fold}.json')
        save_json(context['inner']['pre'],out/f'preprocessing_{fold}_inner.json')
        audit=context['meta'].loc[context['train']|context['valid']].copy()
        audit['fold']=fold;audit['split']=np.where(audit.date.lt(train_end),'train','validation')
        fold_audits.append(audit)
    save_csv(pd.concat(fold_audits),out/'fold_sample_audit.csv')
    modules={f:importlib.import_module(f'models.{f}') for f in args.models}
    grids={f:modules[f].candidates()[:1] if args.smoke else modules[f].candidates() for f in args.models}
    save_json({'folds':FOLDS,'inner_stopping_days':21,'candidates':grids,'seeds':args.seeds,
               'selection':'minimum unweighted mean of three outer-fold ensemble MAEs',
               'final_epochs':'per-seed median of selected candidate inner stopping epochs across folds'},out/'experiment_design.json')
    selected={}
    print(f'Pooled rows={len(data)}; device={device}; models={args.models}',flush=True)
    # Complete all tuning before any final-test predictions.
    for family,module in modules.items():
        candidates=grids[family]
        seeds=args.seeds if family in ['cnn','lstm','cnn_lstm','random_forest'] else [args.seeds[0]]
        candidate_predictions={}
        for candidate_id,config in enumerate(candidates):
            for fold,_,_ in FOLDS:
                c=contexts[fold];arrays,meta=c['arrays'],c['meta'];valid_meta=meta.loc[c['valid']]
                forecasts=[]
                for seed in seeds:
                    t=time.perf_counter()
                    if module.KIND=='baseline':forecast=module.predict(valid_meta)
                    elif module.KIND=='classical':
                        model=module.build(config,seed,args.trees,args.threads)
                        model.fit(design(arrays,c['n_counties'])[c['train']],residual(arrays)[c['train']])
                        forecast=classical_predict(model,arrays,meta,c['valid'],c['n_counties'])
                    else:
                        inner=c['inner']
                        _,epoch,h=fit_neural(module,config,inner['arrays'],inner['meta'],inner['train'],inner['valid'],seed,device,
                            args.epochs,args.patience,args.batch_size,c['n_counties'],'inner_stopping')
                        epochs_lookup[(family,candidate_id,fold,seed)]=epoch
                        history.extend({**r,'model':family,'candidate_id':candidate_id,'fold':fold,'seed':seed} for r in h)
                        model,_,h=fit_neural(module,config,arrays,meta,c['train'],None,seed,device,
                            epoch,args.patience,args.batch_size,c['n_counties'],'outer_refit')
                        history.extend({**r,'model':family,'candidate_id':candidate_id,'fold':fold,'seed':seed} for r in h)
                        forecast=units(predict(model,arrays,c['valid'],device),valid_meta)
                    forecasts.append(forecast)
                    seed_rows.append({'model':family,'candidate_id':candidate_id,'fold':fold,'seed':seed,
                        'epochs':epochs_lookup.get((family,candidate_id,fold,seed)),
                        'seconds':time.perf_counter()-t,**metrics(valid_meta.observed,forecast)})
                forecast=np.mean(forecasts,axis=0)
                row={'model':family,'candidate_id':candidate_id,'fold':fold,'parameters':json.dumps(config),**metrics(valid_meta.observed,forecast)}
                cv_rows.append(row)
                p=valid_meta[['county','date','observed','persistence']].copy()
                p['prediction']=forecast;p['fold']=fold;p['model']=family;p['candidate_id']=candidate_id
                candidate_predictions[(candidate_id,fold)]=p
                print(f'CV {family} candidate={candidate_id} {fold} MAE={row["mae"]:.4f}',flush=True)
        scores=pd.DataFrame([r for r in cv_rows if r['model']==family]).groupby('candidate_id').mae.mean()
        winner=int(scores.idxmin())
        chosen={'candidate_id':winner,'parameters':candidates[winner],'mean_fold_mae':float(scores.min())}
        if module.KIND=='neural':
            chosen['epochs_by_seed']={str(seed):max(1,int(np.median([epochs_lookup[(family,winner,fold,seed)] for fold,_,_ in FOLDS]))) for seed in seeds}
        selected[family]=chosen
        cv_predictions.extend(candidate_predictions[(winner,fold)] for fold,_,_ in FOLDS)
        save_csv(pd.DataFrame(cv_rows),out/'cv_candidate_fold_metrics.csv')
        save_csv(pd.DataFrame(seed_rows),out/'cv_seed_metrics.csv')
        save_csv(pd.DataFrame(history),out/'training_history.csv')
        print('Selected',family,chosen,flush=True)
    save_json(selected,out/'selected_settings.json')
    save_csv(pd.concat(cv_predictions),out/'selected_cv_predictions.csv')
    print('Tuning frozen. Final refit Jan-Sep and exploratory evaluation Oct-Dec.',flush=True)
    final=build_context(data,args.lookback,TEST_START,'2026-01-01')
    arrays,meta=final['arrays'],final['meta'];test_meta=meta.loc[final['valid']]
    save_json(final['pre'],out/'preprocessing_final.json')
    save_csv(meta.assign(split=np.where(final['train'],'refit','test')),out/'final_sample_audit.csv')
    predictions=[];individual=[];manifest=[];parameter_counts=[]
    for family,module in modules.items():
        config=selected[family]['parameters'];forecasts=[]
        seeds=args.seeds if family in ['cnn','lstm','cnn_lstm','random_forest'] else [args.seeds[0]]
        for seed in seeds:
            if module.KIND=='baseline':forecast=module.predict(test_meta)
            elif module.KIND=='classical':
                model=module.build(config,seed,args.trees,args.threads)
                model.fit(design(arrays,final['n_counties'])[final['train']],residual(arrays)[final['train']])
                forecast=classical_predict(model,arrays,meta,final['valid'],final['n_counties'])
                name=f'models/{family}_{seed}.joblib';joblib.dump(model,out/name)
                reloaded=joblib.load(out/name)
                np.testing.assert_allclose(classical_predict(reloaded,arrays,meta,final['valid'],final['n_counties']),forecast)
                manifest.append({'family':family,'seed':seed,'file':name,'format':'joblib'})
            else:
                epoch=selected[family]['epochs_by_seed'][str(seed)]
                model,_,h=fit_neural(module,config,arrays,meta,final['train'],None,seed,device,
                    epoch,args.patience,args.batch_size,final['n_counties'],'final_refit')
                history.extend({**r,'model':family,'candidate_id':selected[family]['candidate_id'],'fold':'final','seed':seed} for r in h)
                scaled=predict(model,arrays,final['valid'],device);forecast=units(scaled,test_meta)
                model_config={k:v for k,v in config.items() if k!='learning_rate'}
                model_config.update(n_counties=final['n_counties'],lookback=args.lookback)
                name=f'models/{family}_{seed}.pt'
                torch.save({'state_dict':{k:v.detach().cpu() for k,v in model.state_dict().items()},'model_config':model_config,
                            'family':family,'seed':seed,'epochs':epoch,'training_end':'2025-09-30'},out/name)
                saved=torch.load(out/name,map_location='cpu',weights_only=True)
                reloaded=module.Model(**saved['model_config']);reloaded.load_state_dict(saved['state_dict'])
                np.testing.assert_allclose(predict(reloaded,arrays,final['valid'],torch.device('cpu')),scaled,atol=5e-4,rtol=5e-4)
                manifest.append({'family':family,'seed':seed,'file':name,'format':'torch_state_dict'})
                parameter_counts.append({'model':family,'seed':seed,'parameters':sum(p.numel() for p in model.parameters())})
            forecasts.append(forecast)
            p=test_meta[['county','date','observed','persistence']].copy();p['model']=family;p['seed']=seed;p['prediction']=forecast
            individual.append(p)
        p=test_meta[['county','date','observed','persistence']].copy();p['model']=family;p['prediction']=np.mean(forecasts,axis=0)
        p['seed_prediction_sd']=np.std(forecasts,axis=0);predictions.append(p)
    predictions=pd.concat(predictions,ignore_index=True)
    if not np.isfinite(predictions.prediction).all():raise AssertionError('Nonfinite prediction')
    save_csv(predictions,out/'test_predictions.csv');save_csv(pd.concat(individual),out/'test_predictions_by_seed.csv')
    save_csv(pd.DataFrame(history),out/'training_history.csv');save_csv(pd.DataFrame(parameter_counts),out/'parameter_counts.csv')
    save_json(manifest,out/'model_manifest.json')
    metadata={'device':str(device),'architecture':platform.machine(),'elapsed_seconds':time.perf_counter()-start,
        'lookback':args.lookback,'seeds':args.seeds,'models':args.models,'test_status':'exploratory: previously inspected outcomes',
        'args':{k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
        'input_sha256':hashlib.sha256(args.data.read_bytes()).hexdigest(),
        'versions':{p:importlib.metadata.version(p) for p in ['torch','numpy','pandas','scikit-learn','openpyxl','matplotlib','joblib']},
        'code_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in list(ROOT.glob('*.py'))+list((ROOT/'models').glob('*.py'))},
        'checkpoint_roundtrip_verified':True}
    save_json(metadata,out/'run_metadata.json')
    from reporting import summarize
    summarize(data,out,args.bootstrap)
    print('Complete:',out,flush=True)


if __name__=='__main__':main()
