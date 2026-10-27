"""Meaningful checks of chronology, preprocessing isolation and model behavior."""
import unittest
import numpy as np
import pandas as pd
import torch
from train_cnn_lstm import FEATURES,CNNLSTM,fit_preprocessing,make_samples


def sample_data():
    frames=[]
    for county,offset in [('a',0),('b',100)]:
        d=pd.DataFrame({'date':pd.date_range('2025-01-01',periods=90),'county':county})
        for j,v in enumerate(FEATURES):d[v]=np.arange(90,dtype=float)+offset+j
        frames.append(d)
    return pd.concat(frames,ignore_index=True)


class Tests(unittest.TestCase):
    def test_training_preprocessing_ignores_future(self):
        d=sample_data();cutoff=pd.Timestamp('2025-03-01')
        a=fit_preprocessing(d,cutoff)
        d.loc[d.date.ge(cutoff),FEATURES]=1e9
        self.assertEqual(a,fit_preprocessing(d,cutoff))

    def test_targets_and_other_counties_do_not_enter_history(self):
        d=sample_data();pre=fit_preprocessing(d,'2025-03-01')
        arrays,meta=make_samples(d,pre,7)
        date=pd.Timestamp('2025-03-10')
        idx=meta.index[meta.county.eq('a') & meta.date.eq(date)][0]
        prior=arrays[0][idx].copy()
        d.loc[(d.county.eq('a') & d.date.ge(date)) | d.county.eq('b'),FEATURES]=999
        later,meta2=make_samples(d,pre,7)
        idx2=meta2.index[meta2.county.eq('a') & meta2.date.eq(date)][0]
        np.testing.assert_array_equal(prior,later[0][idx2])
        self.assertEqual(meta.loc[idx,'window_end'],date-pd.Timedelta(days=1))

    def test_missing_predictor_uses_training_median_and_mask(self):
        d=sample_data();pre=fit_preprocessing(d,'2025-03-01')
        d.loc[d.county.eq('a') & d.date.eq('2025-03-09'),'wind']=np.nan
        arrays,meta=make_samples(d,pre,7)
        i=meta.index[meta.county.eq('a') & meta.date.eq('2025-03-10')][0]
        wind=FEATURES.index('wind');p=pre['counties']['a']
        self.assertAlmostEqual(arrays[0][i,-1,wind],(p['median'][wind]-p['mean'][wind])/p['std'][wind],places=5)
        self.assertEqual(arrays[0][i,-1,wind+7],1)

    def test_missing_previous_pm25_is_not_a_forecast_input(self):
        d=sample_data();pre=fit_preprocessing(d,'2025-03-01')
        d.loc[d.county.eq('a') & d.date.eq('2025-03-09'),'pm25']=np.nan
        _,meta=make_samples(d,pre,7)
        self.assertFalse((meta.county.eq('a') & meta.date.eq('2025-03-10')).any())

    def test_inference_accepts_unknown_future_target(self):
        d=sample_data();pre=fit_preprocessing(d,'2025-03-01')
        arrays,meta=make_samples(d,pre,7,forecast_date='2025-04-01')
        self.assertEqual(len(meta),2)
        self.assertTrue(np.isnan(arrays[-1]).all())
        self.assertTrue(meta.window_end.eq(pd.Timestamp('2025-03-31')).all())

    def test_model_initially_equals_persistence_and_has_finite_gradients(self):
        model=CNNLSTM(2);x=torch.randn(5,14,14);cal=torch.randn(5,5);ids=torch.tensor([0,1,0,1,0])
        model.eval();prediction=model(x,cal,ids)
        torch.testing.assert_close(prediction,x[:,-1,0])
        ((prediction-torch.randn(5))**2).mean().backward()
        self.assertTrue(all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None))


if __name__=='__main__':unittest.main()
