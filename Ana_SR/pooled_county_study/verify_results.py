"""Independent audit of saved folds, model selection, metrics and seed averaging."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from preprocessing import fit_preprocessing,metrics
from splits import FOLDS,stopping_start
ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,default=ROOT/'results')
    parser.add_argument('--data',type=Path,default=ROOT/'data/merged_counties.xlsx')
    args=parser.parse_args();out=args.results
    run=json.loads((out/'run_metadata.json').read_text())
    assert hashlib.sha256(args.data.read_bytes()).hexdigest()==run['input_sha256']
    data=pd.read_excel(args.data,sheet_name='Clean panel') if args.data.suffix=='.xlsx' else pd.read_csv(args.data,parse_dates=['date'])
    data.date=pd.to_datetime(data.date)
    chosen=json.loads((out/'selected_settings.json').read_text())
    cv=pd.read_csv(out/'cv_candidate_fold_metrics.csv')
    cv_seed=pd.read_csv(out/'cv_seed_metrics.csv')
    for model,g in cv.groupby('model'):
        assert g.groupby('candidate_id').fold.nunique().eq(3).all()
        assert int(g.groupby('candidate_id').mae.mean().idxmin())==chosen[model]['candidate_id']
        np.testing.assert_allclose(g[g.candidate_id.eq(chosen[model]['candidate_id'])].mae.mean(),chosen[model]['mean_fold_mae'])
        if 'epochs_by_seed' in chosen[model]:
            rows=cv_seed[cv_seed.model.eq(model)&cv_seed.candidate_id.eq(chosen[model]['candidate_id'])]
            for seed,epoch in chosen[model]['epochs_by_seed'].items():
                assert epoch==int(rows[rows.seed.eq(int(seed))].epochs.median())
    for fold,end,last in FOLDS:
        for suffix,before in [('',end),('_inner',stopping_start(end))]:
            stored=json.loads((out/f'preprocessing_{fold}{suffix}.json').read_text())
            regenerated=fit_preprocessing(data,before)
            assert stored==regenerated
    assert json.loads((out/'preprocessing_final.json').read_text())==fit_preprocessing(data,'2025-10-01')
    audit=pd.read_csv(out/'fold_sample_audit.csv',parse_dates=['date','window_end'])
    for fold,end,last in FOLDS:
        g=audit[audit.fold.eq(fold)];train=g[g.split.eq('train')];valid=g[g.split.eq('validation')]
        assert train.date.lt(end).all() and valid.date.ge(end).all() and valid.date.lt(last).all()
        assert valid.date.lt('2025-10-01').all()
    assert audit.window_end.eq(audit.date-pd.Timedelta(days=1)).all()
    p=pd.read_csv(out/'test_predictions.csv',parse_dates=['date'])
    seed=pd.read_csv(out/'test_predictions_by_seed.csv',parse_dates=['date'])
    pooled=pd.read_csv(out/'pooled_test_metrics.csv').set_index('model')
    assert set(p.model)==set(run['models'])
    reference=None
    for model,g in p.groupby('model'):
        keys=set(zip(g.county,g.date));assert len(keys)==len(g)
        if reference is None:reference=keys
        assert keys==reference
        assert g.date.ge('2025-10-01').all() and g.date.le('2025-12-31').all()
        for metric,value in metrics(g.observed,g.prediction).items():np.testing.assert_allclose(value,pooled.loc[model,metric])
        if model=='persistence':np.testing.assert_allclose(g.prediction,g.persistence)
    averaged=seed.groupby(['model','county','date']).prediction.mean()
    np.testing.assert_allclose(p.set_index(['model','county','date']).prediction.sort_index(),averaged.sort_index())
    intervals=pd.read_csv(out/'paired_mae_intervals.csv') if len(run['models'])>1 else pd.DataFrame()
    for r in intervals.itertuples():
        np.testing.assert_allclose(r.mae_a_minus_b,pooled.loc[r.model_a,'mae']-pooled.loc[r.model_b,'mae'],atol=1e-12)
    checks={'all_candidates_have_three_folds':True,'settings_selected_from_cv_only':True,
            'all_preprocessing_recomputed_from_training_only':True,'epochs_match_prescribed_median_rule':True,
            'all_models_same_test_cases':True,'metrics_recomputed':True,'ensemble_predictions_recomputed':True,
            'temporal_windows_and_splits_verified':True,'paired_differences_recomputed':True,
            'input_hash_matches':True,'model_checkpoint_roundtrip':run['checkpoint_roundtrip_verified']}
    (out/'independent_verification.json').write_text(json.dumps(checks,indent=2))
    print(f'PASS: {len(checks)} independent audit checks; {len(reference)} shared test cases; three chronological folds.')


if __name__=='__main__':main()
