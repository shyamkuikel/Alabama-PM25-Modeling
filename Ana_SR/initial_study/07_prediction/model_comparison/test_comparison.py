import unittest
import numpy as np
import pandas as pd
import torch
from models import ForecastNetwork, NEURAL_MODELS, classical_inputs, residual_target
from compare_models import select_neural_width, uncertainty_table


class ComparisonTests(unittest.TestCase):
    def test_all_encoders_start_at_persistence_and_can_train(self):
        for family in NEURAL_MODELS:
            model=ForecastNetwork(family,3)
            x=torch.randn(5,14,14);cal=torch.randn(5,5);ids=torch.tensor([0,1,2,0,1])
            prediction=model(x,cal,ids)
            torch.testing.assert_close(prediction,x[:,-1,0])
            (prediction-torch.ones(5)).square().mean().backward()
            self.assertTrue(all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None))
            self.assertGreater(model.head[-1].weight.grad.abs().sum().item(),0)

    def test_classical_models_receive_full_history(self):
        x=np.arange(2*14*14,dtype=np.float32).reshape(2,14,14)
        arrays=(x,np.ones((2,5),dtype=np.float32),np.array([0,1]),np.array([3.,4.]))
        design=classical_inputs(arrays,2)
        np.testing.assert_array_equal(design[:,:196],x.reshape(2,-1))
        np.testing.assert_allclose(residual_target(arrays)+x[:,-1,0],arrays[-1])
        np.testing.assert_array_equal(design[:,-2:],np.eye(2))

    def test_width_selection_uses_validation_only(self):
        rows=[dict(width=8,validation_mae=2.,test_mae=0.),dict(width=16,validation_mae=1.,test_mae=10.)]
        self.assertEqual(select_neural_width(rows),(16,1.))

    def test_paired_intervals_for_identical_predictions_are_zero(self):
        rows=[]
        for date in pd.date_range('2025-10-01',periods=14):
            for county in ['a','b']:
                for model in ['cnn','cnn_lstm']:
                    rows.append(dict(date=date,county=county,model=model,observed=2.,prediction=3.))
        result=uncertainty_table(pd.DataFrame(rows),50)
        np.testing.assert_array_equal(result[['mae_a_minus_b','ci_low','ci_high']],0.)


if __name__=='__main__':unittest.main()
