"""Reproduce numerical source comparisons from the archived public-source extracts.

Public downloads and extraction date are recorded in SOURCE_FINDINGS.md.
This identifies matching records, not the original downloader or export history.
"""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
WORKBOOK=ROOT.parents[3]/'Meterological_data_ALAbama_copy.xlsx'
if not WORKBOOK.exists():
    candidates=[ROOT.parents[4]/'Ana_SK'/'Meterological_data_ALAbama.xlsx',
                ROOT.parents[4]/'Ana_SK'/'Meterological data ALAbama .xlsx']
    WORKBOOK=next((p for p in candidates if p.exists()),WORKBOOK)
SITES={'Baldwin':10,'Clay':1,'Dekalb':1003,'Etohaw':10,'Jefferson_NB':23,
       'Mobile':3,'Montgomery':1002,'Morgan':11,'Sumter':3,'Tuscaloosa':11}
COUNTIES={'Dekalb':'DeKalb','Etohaw':'Etowah','Jefferson_NB':'Jefferson'}
STATIONS={'Baldwin':'BFM','Clay':'ASN','Dekalb':'4A9','Etohaw':'GAD',
          'Jefferson_NB':'BHM','Mobile':'BFM','Montgomery':'MXF',
          'Morgan':'DCU','Sumter':'DYA','Tuscaloosa':'TCL'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workbook',type=Path,default=WORKBOOK)
    args=parser.parse_args()
    sheets=pd.read_excel(args.workbook,sheet_name=None)
    epa=pd.read_csv(ROOT/'epa_alabama_88101_2025.csv')
    daily=epa[epa['Sample Duration'].isin(['24 HOUR','24-HR BLK AVG'])].copy()
    # Avoid repeating the same measurement under different standard/event rows.
    # POC distinguishes instruments and is preserved in this exploratory rule.
    daily=daily.drop_duplicates(['County Code','Site Num','POC','Date Local',
                                 'Sample Duration','Arithmetic Mean'])
    comparisons=[];summary=[];sites=[]
    for sheet,s in sheets.items():
        county=COUNTIES.get(sheet,sheet);site=SITES[sheet]
        g=daily[daily['County Name'].eq(county)&daily['Site Num'].eq(site)]
        ref=g.groupby('Date Local')['Arithmetic Mean'].mean().rename('epa')
        d=s.iloc[:,[0,7]].copy();d.columns=['Date Local','workbook']
        d['Date Local']=pd.to_datetime(d['Date Local']).dt.strftime('%Y-%m-%d')
        joined=d.merge(ref,on='Date Local',how='outer')
        joined['sheet']=sheet;joined['difference']=joined.workbook-joined.epa
        joined['both_present']=joined.workbook.notna()&joined.epa.notna()
        joined['exact_match']=joined.both_present&np.isclose(joined.workbook,joined.epa,atol=1e-8,rtol=0)
        comparisons.append(joined)
        summary.append(dict(sheet=sheet,matched=int(joined.exact_match.sum()),
            compared=int(joined.both_present.sum()),workbook_present=int(d.workbook.notna().sum()),
            source_present=len(ref),workbook_only=int((joined.workbook.notna()&joined.epa.isna()).sum()),
            source_only=int((joined.workbook.isna()&joined.epa.notna()).sum())))
        r=g.iloc[0]
        sites.append(dict(sheet=sheet,county=county,aqs_site=f"01-{int(r['County Code']):03}-{site:04}",
            site_name=r['Local Site Name'],latitude=r.Latitude,longitude=r.Longitude,
            units=r['Units of Measure']))
    pd.concat(comparisons).to_csv(ROOT/'pm25_daily_comparison.csv',index=False)
    pd.DataFrame(summary).to_csv(ROOT/'pm25_matching_summary.csv',index=False)
    pd.DataFrame(sites).to_csv(ROOT/'pm25_monitor_locations.csv',index=False)

    weather=pd.read_csv(ROOT/'weather_2025.csv',na_values=['M','T'],low_memory=False)
    weather['date']=pd.to_datetime(weather.valid).dt.normalize()
    for name in ['tmpf','dwpf','sknt']:weather[name]=pd.to_numeric(weather[name],errors='coerce')
    weather['temp_round']=weather.tmpf.round()
    weather['dew_round']=weather.dwpf.round()
    weather['wind_round']=(weather.sknt*1.150779448).round()
    daily=weather.groupby(['station','date'])[['tmpf','dwpf','temp_round','dew_round','wind_round']].mean().reset_index()
    rows=[]
    for sheet,s in sheets.items():
        d=s.iloc[:,:7].copy();d.columns=['date','temp','dew','rh','wind','pressure','rain']
        j=d.merge(daily[daily.station.eq(STATIONS[sheet])],on='date')
        for target,source in [('temp','tmpf'),('temp','temp_round'),('dew','dwpf'),('dew','dew_round'),('wind','wind_round')]:
            both=j[[target,source]].dropna()
            rows.append(dict(sheet=sheet,station=STATIONS[sheet],workbook_column=target,
                comparison_column=source,matched=int(np.isclose(both[target],both[source],atol=1e-8,rtol=0).sum()),
                compared=len(both),mae=float(abs(both[target]-both[source]).mean())))
    pd.DataFrame(rows).to_csv(ROOT/'weather_matching_summary.csv',index=False)
    print(pd.DataFrame(summary).to_string(index=False))
    print('Saved PM2.5 comparisons, station metadata and weather matching summaries.')


if __name__=='__main__':main()
