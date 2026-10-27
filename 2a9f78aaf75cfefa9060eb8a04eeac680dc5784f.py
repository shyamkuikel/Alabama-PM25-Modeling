"""Load trusted local comparison checkpoints and forecast from prior observations."""
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import torch
from data import DEFAULT_WORKBOOK,read_workbook,make_samples,select_device
from models import ForecastNetwork,classical_predict,ALL_MODELS
from compare_models import ROOT,predict_network,original_units


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',type=Path,default=ROOT/'results')
    p.add_argument('--workbook',type=Path,default=DEFAULT_WORKBOOK)
    p.add_argument('--date',required=True)
    p.add_argument('--device',choices=['auto','cpu','mps'],default='auto')
    p.add_argument('--output',type=Path,default=ROOT/'next_day_predictions.csv')
    args=p.parse_args()
    date=pd.Timestamp(args.date).normalize()
    if date<=pd.Timestamp('2025-09-30'):p.error('Date must follow the fitted training period.')
    preprocessing=json.loads((args.results/'preprocessing_final.json').read_text())
    metadata=json.loads((args.results/'run_metadata.json').read_text())
    manifest=json.loads((args.results/'model_manifest.json').read_text())
    data,_=read_workbook(args.workbook)
    arrays,meta=make_samples(data[data.date.lt(date)].copy(),preprocessing,metadata['lookback'],forecast_date=date)
    if meta.empty:p.error('No county has sufficient history and observed previous-day PM2.5.')
    device=select_device(args.device);mask=np.ones(len(meta),dtype=bool)
    predictions={family:[] for family in ALL_MODELS}
    predictions['persistence']=[meta.persistence.to_numpy()]
    for entry in manifest:
        path=args.results/entry['file']
        if entry['format']=='torch_state_dict':
            saved=torch.load(path,map_location='cpu',weights_only=True)
            model=ForecastNetwork(**saved['model_config']).to(device)
            model.load_state_dict(saved['state_dict'])
            scaled=predict_network(model,arrays,mask,device)
        else:
            model=joblib.load(path)
            scaled=classical_predict(model,arrays,len(preprocessing['county_ids']),mask)
        predictions[entry['family']].append(original_units(scaled,meta))
    rows=[]
    for family,values in predictions.items():
        if not values:raise ValueError(f'Missing saved family: {family}')
        result=meta[['county','date','window_start','window_end','persistence']].copy()
        result['model']=family;result['prediction']=np.mean(values,axis=0)
        result['seed_prediction_sd']=np.std(values,axis=0)
        rows.append(result)
    result=pd.concat(rows,ignore_index=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    result.to_csv(args.output,index=False,float_format='%.17g')
    print(result.to_string(index=False))
    print('Saved:',args.output.resolve())


if __name__=='__main__':main()
