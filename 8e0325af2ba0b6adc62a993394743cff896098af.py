"""Merge county sheets, preserve raw observations and prepare a non-imputed panel."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
from preprocessing import read_workbook,COLUMNS,NAMES,FEATURES
ROOT=Path(__file__).resolve().parent
DEFAULT_WORKBOOK=ROOT.parent/'Meterological_data_ALAbama_copy.xlsx'


def prepare(workbook=DEFAULT_WORKBOOK,output=ROOT/'data',negative_policy='missing'):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    raw=[]
    for sheet,d in pd.read_excel(workbook,sheet_name=None).items():
        d=d[list(COLUMNS)].rename(columns=COLUMNS).copy()
        d['county']=NAMES.get(sheet,sheet);d['source_sheet']=sheet
        d['source_excel_row']=np.arange(2,len(d)+2)
        d['date']=pd.to_datetime(d.date).dt.normalize()
        raw.append(d)
    raw=pd.concat(raw,ignore_index=True).sort_values(['date','county']).reset_index(drop=True)
    raw=raw[['date','county',*FEATURES,'source_sheet','source_excel_row']]
    if raw.duplicated(['date','county']).any():raise ValueError('Duplicate county/date key')
    clean,flags=read_workbook(workbook)
    negative=clean.pm25.lt(0)
    if negative_policy=='missing':
        clean.loc[negative,'pm25']=np.nan
        flags.loc[flags.action.eq('negative_reading_retained'),'action']='negative_pm25_set_missing'
    clean=clean.merge(raw[['date','county','source_sheet','source_excel_row']],on=['date','county'],how='left',validate='one_to_one')
    clean['pm25_negative_in_source']=clean.set_index(['date','county']).index.isin(raw.loc[raw.pm25.lt(0)].set_index(['date','county']).index)
    clean=clean.sort_values(['date','county']).reset_index(drop=True)
    clean=clean[['date','county',*FEATURES,'source_sheet','source_excel_row','pm25_negative_in_source']]
    for name,frame in [('merged_raw',raw),('merged_clean',clean),('cleaning_log',flags)]:frame.to_csv(output/f'{name}.csv',index=False,float_format='%.17g')
    summary=[]
    for county,g in clean.groupby('county'):
        summary.append({'county':county,'rows':len(g),'observed_pm25':int(g.pm25.notna().sum()),
                        'missing_pm25':int(g.pm25.isna().sum()),'negative_source_pm25':int(g.pm25_negative_in_source.sum()),
                        **{f'missing_{f}':int(g[f].isna().sum()) for f in FEATURES[1:]}})
    summary=pd.DataFrame(summary);summary.to_csv(output/'quality_summary.csv',index=False)
    dictionary=[['date','Local calendar date','2025-01-01 to 2025-12-31'],['county','Normalized county label','Monitor observations, not spatial county averages'],
        ['pm25','Daily PM2.5','Matching EPA records support micrograms/m³, local conditions'],
        ['temperature','Daily weather input','Fahrenheit supported by source matching'],['dew_point','Daily weather input','Fahrenheit supported by source matching'],
        ['humidity','Relative humidity','Percent; source processing unverified'],['wind','Wind speed','mph supported by source reconstruction'],
        ['pressure','Pressure input','Exact pressure definition unverified'],['rain','Precipitation input','Unit and daily aggregation unverified'],
        ['source_sheet','Original worksheet name','Preserved for provenance'],['source_excel_row','Original Excel row','Header is row 1'],
        ['pm25_negative_in_source','Negative source measurement flag','True even when cleaned PM2.5 is missing']]
    payload={'raw':json.loads(raw.to_json(orient='records',date_format='iso',double_precision=15)),
             'clean':json.loads(clean.to_json(orient='records',date_format='iso',double_precision=15)),
             'quality':json.loads(summary.to_json(orient='records')),'dictionary':dictionary}
    (output/'workbook_payload.json').write_text(json.dumps(payload))
    metadata={'source_workbook':str(Path(workbook).resolve()),'source_sha256':hashlib.sha256(Path(workbook).read_bytes()).hexdigest(),
              'rows_raw':len(raw),'rows_clean':len(clean),'counties':clean.county.nunique(),
              'negative_policy':negative_policy,'observed_pm25':int(clean.pm25.notna().sum()),
              'cleaning':'Normalize names/dates, enforce unique keys, numeric/finite values; insert missing daily rows; replace impossible weather and joint zero placeholders with missing. No target imputation, future interpolation, clipping or data-driven outlier deletion.'}
    (output/'data_metadata.json').write_text(json.dumps(metadata,indent=2))
    print(json.dumps(metadata,indent=2));return clean


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workbook',type=Path,default=DEFAULT_WORKBOOK)
    p.add_argument('--output',type=Path,default=ROOT/'data')
    p.add_argument('--negative-policy',choices=['missing','retain'],default='missing')
    a=p.parse_args();prepare(a.workbook,a.output,a.negative_policy)
