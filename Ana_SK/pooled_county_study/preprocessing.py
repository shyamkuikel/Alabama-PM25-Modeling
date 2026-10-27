"""County-safe daily histories and training-only preprocessing, reused from the tested initial study."""
from pathlib import Path
import random
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader,TensorDataset
FEATURES=['pm25','temperature','dew_point','humidity','wind','pressure','rain']
COLUMNS=dict(zip(['Only_Date','Daily Mean PM2.5 Concentration','Temperature','Dew Point','Relative Humidity','Wind Speed','Pressure','Precipitation'],['date',*FEATURES]))
NAMES={'Dekalb':'DeKalb','Etohaw':'Etowah','Jefferson_NB':'Jefferson'}
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
