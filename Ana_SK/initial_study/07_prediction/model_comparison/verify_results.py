"""Independently audit saved evaluation tables without retraining."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from models import ALL_MODELS,NEURAL_MODELS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,default=Path(__file__).resolve().parent/'results')
    out=parser.parse_args().results
    p=pd.read_csv(out/'test_predictions.csv',parse_dates=['date'])
    seeds=pd.read_csv(out/'test_predictions_by_seed.csv')
    score=pd.read_csv(out/'pooled_test_metrics.csv').set_index('model')
    assert set(p.model)==set(ALL_MODELS)
    reference=None
    for model,g in p.groupby('model'):
        keys=set(zip(g.county,g.date))
        assert len(keys)==len(g)
        if reference is None:reference=keys
        assert keys==reference
        assert g.date.ge('2025-10-01').all() and g.date.le('2025-12-31').all()
        np.testing.assert_allclose(abs(g.prediction-g.observed).mean(),score.loc[model,'mae'])
        if model=='persistence':np.testing.assert_allclose(g.prediction,g.persistence)
    averaged=seeds.groupby(['model','county','date']).prediction.mean()
    ensemble=p[p.model.isin(seeds.model.unique())].copy()
    ensemble['date']=ensemble.date.dt.strftime('%Y-%m-%d')
    np.testing.assert_allclose(ensemble.set_index(['model','county','date']).prediction.sort_index(),averaged.sort_index())
    selection=pd.read_csv(out/'validation_scores.csv')
    chosen=json.loads((out/'selected_settings.json').read_text())
    for family in NEURAL_MODELS:
        rows=selection[selection.model.eq(family)]
        assert int(rows.groupby('width').validation_mae.mean().idxmin())==chosen[family]['width']
    rows=selection[selection.model.eq('ridge')]
    assert rows.loc[rows.validation_mae.idxmin(),'alpha']==chosen['ridge']['alpha']
    intervals=pd.read_csv(out/'paired_model_mae_intervals.csv')
    for r in intervals.itertuples():
        np.testing.assert_allclose(r.mae_a_minus_b,score.loc[r.model_a,'mae']-score.loc[r.model_b,'mae'],atol=1e-12)
    audit=pd.read_csv(out/'final_sample_audit.csv',parse_dates=['date','window_end'])
    assert (audit.window_end==audit.date-pd.Timedelta(days=1)).all()
    assert all(json.loads((out/'verification.json').read_text()).values())
    print(f'PASS: six aligned model families, {len(reference)} cases each; metrics, seed averaging, selection, paired differences and temporal audits.')


if __name__=='__main__':main()
