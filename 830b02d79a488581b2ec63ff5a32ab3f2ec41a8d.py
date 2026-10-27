"""Comparable metrics and exploratory calendar-block uncertainty."""
import itertools,json
from pathlib import Path
import numpy as np
import pandas as pd
from preprocessing import metrics

def markdown_table(frame):
    rows=[list(frame.columns)]
    for row in frame.itertuples(index=False,name=None):
        rows.append([f'{v:.4f}' if isinstance(v,(float,np.floating)) else str(v) for v in row])
    return '| '+' | '.join(map(str,rows[0]))+' |\n| '+' | '.join(['---']*len(rows[0]))+' |\n'+'\n'.join('| '+' | '.join(row)+' |' for row in rows[1:])

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


def summarize(data,out,bootstrap):
    p=pd.read_csv(out/'test_predictions.csv',parse_dates=['date'])
    thresholds=data[data.date.lt('2025-10-01')].groupby('county').pm25.quantile(.95)
    pooled,county=evaluate(p,thresholds)
    pooled.to_csv(out/'pooled_test_metrics.csv',index=False)
    county.to_csv(out/'county_test_metrics.csv',index=False)
    thresholds.rename('training_p95').to_csv(out/'high_day_thresholds.csv')
    intervals=uncertainty_table(p,bootstrap) if p.model.nunique()>1 else pd.DataFrame()
    intervals.to_csv(out/'paired_mae_intervals.csv',index=False)
    individual=pd.read_csv(out/'test_predictions_by_seed.csv')
    seed_metrics=pd.DataFrame([{'model':m,'seed':s,**metrics(g.observed,g.prediction)} for (m,s),g in individual.groupby(['model','seed'])])
    seed_metrics.to_csv(out/'seed_test_metrics.csv',index=False)
    selected=json.loads((out/'selected_settings.json').read_text())
    cv=pd.read_csv(out/'cv_candidate_fold_metrics.csv')
    chosen=cv[cv.apply(lambda r:int(r.candidate_id)==selected[r.model]['candidate_id'],axis=1)]
    cv_summary=chosen.groupby('model').agg(mean_fold_mae=('mae','mean'),fold_mae_sd=('mae','std'),
        mean_fold_rmse=('rmse','mean'),validation_cases=('n','sum')).reset_index().sort_values('mean_fold_mae')
    cv_summary.to_csv(out/'cv_selected_summary.csv',index=False)
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    for ax,frame,value,title in [(axes[0],cv_summary,'mean_fold_mae','Three-fold validation'),(axes[1],pooled,'mae','October–December exploratory test')]:
        ax.barh(frame.model,frame[value],color=['#cd773e' if m=='cnn_lstm' else '#287b96' for m in frame.model]);ax.invert_yaxis()
        ax.set(xlabel='MAE (µg/m³)',title=title,xlim=(0,frame[value].max()*1.16))
        for i,v in enumerate(frame[value]):ax.text(v+.02,i,f'{v:.3f}',va='center')
    fig.tight_layout();fig.savefig(out/'model_comparison.png',dpi=200);plt.close(fig)
    pivot=county.pivot(index='county',columns='model',values='mae')
    fig,ax=plt.subplots(figsize=(10,6));im=ax.imshow(pivot,aspect='auto',cmap='viridis')
    ax.set_xticks(range(len(pivot.columns)),pivot.columns,rotation=30,ha='right');ax.set_yticks(range(len(pivot)),pivot.index)
    ax.set_title('County test MAE on shared eligible dates')
    for i in range(len(pivot)):
        for j in range(len(pivot.columns)):
            v=pivot.iloc[i,j];ax.text(j,i,f'{v:.2f}',ha='center',va='center',color='white' if im.norm(v)<.65 else 'black')
    fig.colorbar(im,ax=ax,label='MAE (µg/m³)');fig.tight_layout();fig.savefig(out/'county_mae.png',dpi=200);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4.5))
    for model,g in chosen.groupby('model'):ax.plot(g.fold,g.mae,marker='o',label=model)
    ax.set(xlabel='Expanding-window fold',ylabel='Outer validation MAE (µg/m³)',title='Selected settings: performance varies across time')
    ax.legend(ncol=3);fig.tight_layout();fig.savefig(out/'validation_by_fold.png',dpi=200);plt.close(fig)
    reference=None
    for model,g in p.groupby('model'):
        keys=set(zip(g.county,g.date))
        if reference is None:reference=keys
        assert keys==reference and len(keys)==len(g)
    verify={'same_test_cases':True,'finite_predictions':bool(np.isfinite(p.prediction).all()),
            'test_after_selection':bool(p.date.ge('2025-10-01').all()),
            'selected_candidates_minimize_mean_cv_mae':all(selected[m]['candidate_id']==int(g.groupby('candidate_id').mae.mean().idxmin()) for m,g in cv.groupby('model'))}
    assert all(verify.values())
    (out/'verification.json').write_text(json.dumps(verify,indent=2))
    report='# Pooled county PM2.5 study with three-fold time-series validation\n\n'
    report+='## Data and cleaning\n\n'
    report+=f'Ten county sheets were merged into {len(data):,} county-day rows, with {data.pm25.notna().sum():,} observed cleaned PM2.5 values. County identity and original sheet/row provenance remain available. Raw observations are preserved separately. Impossible weather placeholders are missing in the analysis copy. By default, negative PM2.5 measurements are missing for both predictors and targets, not clipped to zero. Training-period imputation is performed separately inside each fold; the merged cleaned dataset itself is not globally imputed.\n\n'
    report+='## Validation and tuning\n\n'
    report+='Fold 1: train Jan–Mar, validate Apr–May. Fold 2: train Jan–May, validate Jun–Jul. Fold 3: train Jan–Jul, validate Aug–Sep. All counties share date boundaries. Each 14-day sequence stays within a county and ends the day before its target. Outer validation measures daily one-step forecasts using previously observed days; it is not a recursive forecast made two months in advance.\n\n'
    report+='Neural early stopping uses only the final 21 days inside each outer training period, with independently fitted inner preprocessing. The model is then refitted on the full outer training period for that duration before scoring outer validation. Candidate settings minimize the unweighted mean of three outer-fold ensemble MAEs. Final neural epochs are each seed’s median stopping duration for the selected candidate across folds. All settings are frozen before Jan–Sep final fitting and Oct–Dec scoring. This is temporal cross-validation with inner stopping, not a fully nested outer performance-estimation study; reported selected CV scores also participated in selection.\n\n'
    report+='Persistence has no trainable parameters or hyperparameters. Ridge tunes alpha; forest tunes depth and leaf size; CNN, LSTM and CNN-LSTM each tune width and learning rate. Neural loss is standardized L1, classical fits use squared error, and parameter counts/tuning budgets differ. Lookback, convolution kernel, dropout and other fixed settings are documented rather than exhaustively searched. All learned models predict a correction to persistence from the same histories, missingness, calendar and county information.\n\n'
    report+='## Selected cross-validation results\n\n'+markdown_table(cv_summary)+'\n\nFold SD describes variation across three time periods, not a standard error.\n\n'
    report+='## Exploratory test results\n\n'+markdown_table(pooled[['model','n','mae','rmse','bias','r_squared','high_days_n','high_days_mae']])+'\n\n'
    report+='Stochastic-family primary predictions average all declared seeds, including the forest. Individual-run metrics are saved separately. High days use each county’s Jan–Sep 95th percentile; their small count limits conclusions about extreme pollution.\n\n'
    if 'cnn_lstm' in set(p.model) and 'lstm' in set(p.model):
        row=intervals[((intervals.model_a=='cnn_lstm')&(intervals.model_b=='lstm'))].iloc[0]
        report+=f'CNN-LSTM minus LSTM test MAE difference: {row.mae_a_minus_b:.4f} µg/m³, paired 95% block-bootstrap interval [{row.ci_low:.4f}, {row.ci_high:.4f}]. '
        report+=('The interval crosses zero, so this experiment does not clearly distinguish their average error.\n\n' if row.ci_low<=0<=row.ci_high else 'The pointwise interval favors the model with lower error, conditional on these fitted models and dates.\n\n')
    report+='## Conclusions and limits\n\n'
    winner=pooled.iloc[0];report+=f'The lowest observed test MAE was {winner.mae:.4f} for {winner.model}. This ranking is descriptive and does not establish performance in a new year or county. Compare CV consistency, uncertainty, county results and high-day errors before choosing a model.\n\n'
    report+='The test months were previously inspected in earlier studies, so this remains exploratory. Pooling increases training rows but not years or independent seasonal cycles. Adjacent counties and duplicated weather inputs create dependence. A seven-day paired calendar-block bootstrap keeps counties together; its intervals are pointwise, not adjusted for multiple comparisons, and condition on the fitted ensembles. Monthly and annual distribution changes remain a concern. Source matching supports PM2.5 units, but weather provenance, pressure/precipitation definitions and real-time availability remain partly unresolved. These measurements represent monitoring sites within counties, not county-wide averages. Negative-value removal changes eligibility compared with the earlier study; this is a new experiment, not a direct replication. Additional untouched years and an explicitly defined peak-prediction objective are needed for stronger conclusions.\n\n'
    report+='## Selected settings\n\n```json\n'+json.dumps(selected,indent=2)+'\n```\n'
    (out/'REPORT.md').write_text(report)
    print(pooled.to_string(index=False),flush=True)
