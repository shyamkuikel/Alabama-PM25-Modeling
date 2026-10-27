"""Load one saved CNN-LSTM checkpoint and predict a specified date from prior data."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from train_cnn_lstm import CNNLSTM,DEFAULT_WORKBOOK,read_workbook,make_samples,predict,select_device


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--workbook',type=Path,default=DEFAULT_WORKBOOK)
    p.add_argument('--date',required=True,help='Forecast target date, e.g. 2026-01-01')
    p.add_argument('--device',choices=['auto','cpu','mps'],default='auto')
    p.add_argument('--output',type=Path,default=Path('next_day_predictions.csv'))
    args=p.parse_args()
    checkpoint=torch.load(args.checkpoint,map_location='cpu',weights_only=True)
    date=pd.Timestamp(args.date).normalize()
    if date<=pd.Timestamp(checkpoint['training_end']):
        p.error('Forecast date must be after the checkpoint training period.')
    data,_=read_workbook(args.workbook)
    # Remove target-day and later values even if present in the workbook.
    data=data[data.date.lt(date)].copy()
    if data.empty:p.error('No observations precede the requested date.')
    arrays,meta=make_samples(data,checkpoint['preprocessing'],checkpoint['lookback'],forecast_date=date)
    device=select_device(args.device)
    model=CNNLSTM(**checkpoint['model_config']).to(device)
    model.load_state_dict(checkpoint['state_dict'])
    scaled=predict(model,arrays,np.ones(len(meta),dtype=bool),device)
    result=meta[['county','date','window_start','window_end','persistence']].copy()
    result['prediction']=scaled*meta.target_std.to_numpy()+meta.target_mean.to_numpy()
    result['model_seed']=checkpoint['seed']
    args.output.parent.mkdir(parents=True,exist_ok=True)
    result.to_csv(args.output,index=False,float_format='%.17g')
    absent=set(checkpoint['preprocessing']['county_ids'])-set(result.county)
    print(result.to_string(index=False))
    if absent:print('Not predicted (insufficient history or missing previous-day PM2.5):',', '.join(sorted(absent)))
    print('Saved:',args.output.resolve())


if __name__=='__main__':main()
