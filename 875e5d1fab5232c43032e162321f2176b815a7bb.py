"""Forecast a specified date from a merged cleaned panel and saved final models."""
import argparse,importlib,json
from pathlib import Path
import numpy as np
import pandas as pd
import torch,joblib
from preprocessing import make_samples,predict
from training import units,classical_predict,select_device
ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',type=Path,default=ROOT/'results')
    p.add_argument('--data',type=Path,default=ROOT/'data/merged_clean.csv')
    p.add_argument('--date',required=True)
    p.add_argument('--device',choices=['auto','cpu','mps'],default='auto')
    p.add_argument('--output',type=Path,default=ROOT/'next_day_predictions.csv')
    args=p.parse_args();date=pd.Timestamp(args.date).normalize()
    if date<=pd.Timestamp('2025-09-30'):p.error('Date must follow training period.')
    pre=json.loads((args.results/'preprocessing_final.json').read_text())
    run=json.loads((args.results/'run_metadata.json').read_text())
    manifest=json.loads((args.results/'model_manifest.json').read_text())
    data=(pd.read_excel(args.data,sheet_name='Clean panel') if args.data.suffix.lower()=='.xlsx'
          else pd.read_csv(args.data,parse_dates=['date']))
    data['date']=pd.to_datetime(data.date).dt.normalize()
    arr,meta=make_samples(data[data.date.lt(date)],pre,run['lookback'],forecast_date=date)
    mask=np.ones(len(meta),dtype=bool);device=select_device(args.device)
    values={f:[] for f in run['models']}
    if 'persistence' in values:values['persistence']=[meta.persistence.to_numpy()]
    for entry in manifest:
        if entry['format']=='torch_state_dict':
            saved=torch.load(args.results/entry['file'],map_location='cpu',weights_only=True)
            model=importlib.import_module('models.'+entry['family']).Model(**saved['model_config']).to(device)
            model.load_state_dict(saved['state_dict'])
            pred=units(predict(model,arr,mask,device),meta)
        else:
            model=joblib.load(args.results/entry['file'])
            pred=classical_predict(model,arr,meta,mask,len(pre['county_ids']))
        values[entry['family']].append(pred)
    frames=[]
    for family,preds in values.items():
        if not preds:raise ValueError(f'No checkpoint for {family}')
        d=meta[['county','date','window_start','window_end','persistence']].copy()
        d['model']=family;d['prediction']=np.mean(preds,axis=0);d['seed_prediction_sd']=np.std(preds,axis=0)
        frames.append(d)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    pd.concat(frames).to_csv(args.output,index=False,float_format='%.17g')
    print('Saved:',args.output.resolve())


if __name__=='__main__':main()
