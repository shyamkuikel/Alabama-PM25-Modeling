"""Compare daily PM2.5 association with official Census county adjacency."""
from pathlib import Path
import hashlib,itertools,json,os
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.mplconfig'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    data=pd.read_csv(ROOT.parent/'analysis_ready_data.csv',parse_dates=['date'])
    x=data.pivot(index='date',columns='county',values='pm25').sort_index()
    x=x.reindex(pd.date_range('2025-01-01','2025-12-31'))
    residual=x-x.groupby(x.index.month).transform('mean')
    adjacency=pd.read_csv(ROOT/'county_adjacency2025.txt',sep='|',dtype={'County GEOID':str,'Neighbor GEOID':str})
    adjacency=adjacency[adjacency['County GEOID'].str.startswith('01')&adjacency['Neighbor GEOID'].str.startswith('01')].copy()
    adjacency['a']=adjacency['County Name'].str.replace(' County, AL','',regex=False)
    adjacency['b']=adjacency['Neighbor Name'].str.replace(' County, AL','',regex=False)
    adjacency=adjacency[adjacency.a.isin(x.columns)&adjacency.b.isin(x.columns)&adjacency.a.lt(adjacency.b)]
    edges={tuple(r[['a','b']]):r.Length for _,r in adjacency.iterrows()}
    assert set(edges)=={('Baldwin','Mobile'),('DeKalb','Etowah'),('Jefferson','Tuscaloosa')}
    rng=np.random.default_rng(20251011)
    indices=[((rng.integers(0,len(x),size=53)[:,None]+np.arange(7))%len(x)).ravel()[:len(x)] for _ in range(1000)]
    rows=[]
    for a,b in itertools.combinations(x.columns,2):
        paired=x[[a,b]].dropna();adj=(a,b) in edges
        row=dict(county_a=a,county_b=b,adjacent=adj,paired_days=len(paired),
                 pearson_r=paired[a].corr(paired[b]),spearman_r=paired[a].corr(paired[b],method='spearman'),
                 month_demeaned_r=residual[a].corr(residual[b]),shared_boundary_km=edges.get((a,b),0)/1000,
                 mean_a_on_paired_days=paired[a].mean(),mean_b_on_paired_days=paired[b].mean())
        if adj:
            for label,frame in [('raw',x),('month_demeaned',residual)]:
                arr=frame[[a,b]].to_numpy();draws=[]
                for ix in indices:
                    sample=arr[ix];sample=sample[np.isfinite(sample).all(axis=1)]
                    draws.append(np.corrcoef(sample.T)[0,1])
                row[label+'_ci_low'],row[label+'_ci_high']=np.quantile(draws,[.025,.975])
        rows.append(row)
    pairs=pd.DataFrame(rows)
    pairs['raw_rank']=pairs.pearson_r.rank(ascending=False,method='min').astype(int)
    pairs=pairs.sort_values('pearson_r',ascending=False)
    pairs.to_csv(ROOT/'all_county_pairs.csv',index=False)
    adjacent=pairs[pairs.adjacent].copy();adjacent.to_csv(ROOT/'adjacent_county_pairs.csv',index=False)
    summary=pairs.groupby('adjacent').agg(pairs=('pearson_r','size'),mean_raw_r=('pearson_r','mean'),
                  mean_month_demeaned_r=('month_demeaned_r','mean')).reset_index()
    summary.to_csv(ROOT/'adjacent_vs_nonadjacent.csv',index=False)
    # Reconcile all 45 correlations with the earlier study.
    old=pd.read_csv(ROOT.parent/'06_simultaneous_peaks/raw_county_correlations.csv',index_col=0)
    for r in pairs.itertuples():np.testing.assert_allclose(r.pearson_r,old.loc[r.county_a,r.county_b],atol=1e-12)
    fig,axes=plt.subplots(1,2,figsize=(12,4.7))
    for ax,column,title in zip(axes,['pearson_r','month_demeaned_r'],['Daily PM2.5','After removing monthly averages']):
        for i,flag in enumerate([False,True]):
            values=pairs.loc[pairs.adjacent.eq(flag),column].to_numpy()
            offsets=np.linspace(-.12,.12,len(values))
            ax.scatter(i+offsets,values,s=30 if not flag else 65,color='#9aaeb8' if not flag else '#237c9b',alpha=.8)
            ax.plot([i-.16,i+.16],[values.mean()]*2,color='#172f3b',lw=2)
        ax.set_xticks([0,1],['Nonadjacent\n42 pairs','Adjacent\n3 pairs'])
        ax.set(title=title,ylabel='Pearson correlation',ylim=(0,1),xlim=(-.5,1.5))
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Neighboring study counties are correlated—but adjacency is not required',fontsize=13)
    fig.text(.5,.015,'Each point is a county pair; horizontal lines show group means. Pairs are not independent.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.04,1,.94]);fig.savefig(ROOT/'adjacency_correlations.png',dpi=220);plt.close(fig)
    table='| Adjacent pair | Paired days | Daily r | Monthly-adjusted r | Daily r interval |\n|---|---:|---:|---:|---|\n'
    for r in adjacent.itertuples():
        table+=f'| {r.county_a}–{r.county_b} | {r.paired_days} | {r.pearson_r:.3f} | {r.month_demeaned_r:.3f} | [{r.raw_ci_low:.3f}, {r.raw_ci_high:.3f}] |\n'
    avg=summary.set_index('adjacent')
    report='# Adjacent counties and daily PM2.5\n\n'
    report+='There are three adjacent pairs among the ten study counties. All three show positive daily association that persists after removing monthly averages.\n\n'+table
    report+=f'\nMean pairwise correlation is {avg.loc[True,"mean_raw_r"]:.3f} for the three adjacent pairs versus {avg.loc[False,"mean_raw_r"]:.3f} for the 42 nonadjacent pairs. After monthly demeaning, the corresponding means are {avg.loc[True,"mean_month_demeaned_r"]:.3f} and {avg.loc[False,"mean_month_demeaned_r"]:.3f}. These are unweighted descriptive means, not an independent-samples significance test.\n\n'
    report+='DeKalb–Etowah has the highest raw correlation of all 45 study pairs. But nonadjacent DeKalb–Morgan and Etowah–Morgan are also strongly correlated. Shared borders are therefore not necessary for synchronized pollution variation. Correlation describes movement together, not equal concentrations or evidence that one county causes pollution in another.\n\n'
    report+='Methods: official 2025 Census adjacency list, including water boundaries and point contacts; all three observed study pairs have positive shared-boundary length. Daily Pearson/Spearman correlations use pairwise observed PM2.5 without imputation. Monthly demeaning subtracts each county’s own monthly average; it removes broad monthly seasonality, not all weather effects or trends. Negative measurements remain, consistent with the earlier study. Intervals for adjacent pairs use 1,000 circular seven-day calendar-block bootstrap samples, retaining missingness and resampling both counties together. Monthly-adjusted intervals condition on the fitted monthly means. Intervals are exploratory, pointwise, not adjusted for multiple comparisons; block length is fixed.\n\n'
    report+='Limits: only three adjacent pairs, selected monitors from ten of Alabama’s 67 counties, one year of measurements and dependent pairwise observations. This cannot establish a general adjacency effect, pollution transport or causality. Baldwin and Mobile share weather inputs in the workbook; weather-independent synchrony has not been established. County adjacency is also an imperfect measure of distance between the actual monitors. Future work could examine monitor distance, wind direction, regional weather and additional years. When building forecasts, test other-county lagged observations using chronological validation and realistic reporting availability; do not use unavailable same-day measurements.\n\n'
    report+='Source: [US Census Bureau 2025 County Adjacency File](https://www.census.gov/geographies/reference-files/time-series/geo/county-adjacency.2025.html). All 45 raw correlations were verified against the earlier simultaneous-peaks analysis. No models were retrained.\n'
    (ROOT/'REPORT.md').write_text(report)
    (ROOT/'metadata.json').write_text(json.dumps({'adjacency_source':'https://www2.census.gov/geo/docs/reference/county_adjacency/county_adjacency2025.txt',
        'adjacency_sha256':hashlib.sha256((ROOT/'county_adjacency2025.txt').read_bytes()).hexdigest(),
        'pm25_input_sha256':hashlib.sha256((ROOT.parent/'analysis_ready_data.csv').read_bytes()).hexdigest(),
        'seed':20251011,'bootstrap_replicates':1000,'block_days':7,'all_45_correlations_match_previous_analysis':True},indent=2))
    print(adjacent.to_string(index=False));print(summary.to_string(index=False))


if __name__=='__main__':main()
