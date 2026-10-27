import unittest,importlib
import numpy as np
import pandas as pd
import torch
from preprocessing import FEATURES,fit_preprocessing,make_samples
from splits import FOLDS,masks,stopping_start
from training import design,residual


def fixture():
    days=pd.date_range('2025-01-01',periods=365)
    frames=[]
    for county,offset in [('a',0),('b',100)]:
        d=pd.DataFrame({'date':days,'county':county})
        for j,f in enumerate(FEATURES):d[f]=np.arange(365,dtype=float)+offset+j
        frames.append(d)
    return pd.concat(frames,ignore_index=True)


class PipelineTests(unittest.TestCase):
    def test_preprocessing_cannot_see_validation_or_test(self):
        data=fixture();pre=fit_preprocessing(data,'2025-04-01')
        altered=data.copy();altered.loc[altered.date.ge('2025-04-01'),FEATURES]=1e9
        self.assertEqual(pre,fit_preprocessing(altered,'2025-04-01'))

    def test_folds_separate_target_dates_and_keep_test_out(self):
        data=fixture();arr,meta=make_samples(data,fit_preprocessing(data,'2025-04-01'),14)
        for _,end,last in FOLDS:
            train,valid=masks(meta,end,last)
            self.assertLess(meta.loc[train,'date'].max(),meta.loc[valid,'date'].min())
            self.assertTrue(meta.loc[valid,'date'].lt('2025-10-01').all())
            inner_train,inner_valid=masks(meta,stopping_start(end),end)
            self.assertTrue((inner_train|inner_valid)[train].all())
            self.assertFalse((inner_train|inner_valid)[valid].any())

    def test_windows_do_not_cross_counties_or_include_target(self):
        data=fixture();pre=fit_preprocessing(data,'2025-04-01');arr,meta=make_samples(data,pre,14)
        for i in [0,100,len(meta)-1]:
            row=meta.iloc[i];raw=data[(data.county==row.county)&data.date.between(row.window_start,row.window_end)].pm25.to_numpy()
            p=pre['counties'][row.county]
            np.testing.assert_allclose(arr[0][i,:,0]*p['std'][0]+p['mean'][0],raw,atol=1e-4)
        self.assertTrue(meta.window_end.eq(meta.date-pd.Timedelta(days=1)).all())

    def test_missing_previous_day_and_targets_are_excluded(self):
        data=fixture();data.loc[(data.county=='a')&data.date.eq('2025-05-01'),'pm25']=np.nan
        _,meta=make_samples(data,fit_preprocessing(data,'2025-04-01'),14)
        self.assertFalse(((meta.county=='a')&meta.date.isin(pd.to_datetime(['2025-05-01','2025-05-02']))).any())

    def test_missing_older_input_gets_mask_without_future_fill(self):
        data=fixture();data.loc[(data.county=='a')&data.date.eq('2025-01-10'),'temperature']=np.nan
        pre=fit_preprocessing(data,'2025-04-01');arr,meta=make_samples(data,pre,14)
        row=meta[(meta.county=='a')&meta.date.eq('2025-01-15')].index[0]
        self.assertEqual(arr[0][row,9,8],1)
        p=pre['counties']['a'];self.assertAlmostEqual(float(arr[0][row,9,1]*p['std'][1]+p['mean'][1]),p['median'][1],places=4)

    def test_models_initialize_to_persistence_and_train(self):
        for family in ['cnn','lstm','cnn_lstm']:
            model=importlib.import_module('models.'+family).Model(2)
            x=torch.randn(4,14,14);cal=torch.randn(4,5);ids=torch.tensor([0,1,0,1])
            prediction=model(x,cal,ids);torch.testing.assert_close(prediction,x[:,-1,0])
            (prediction-1).square().mean().backward()
            self.assertGreater(model.head[-1].weight.grad.abs().sum().item(),0)

    def test_classical_models_receive_same_full_histories(self):
        data=fixture();arr,_=make_samples(data,fit_preprocessing(data,'2025-04-01'),14)
        d=design(arr,2);np.testing.assert_array_equal(d[:,:196],arr[0].reshape(len(arr[0]),-1))
        np.testing.assert_allclose(residual(arr)+arr[0][:,-1,0],arr[-1],atol=1e-6)


if __name__=='__main__':unittest.main()
