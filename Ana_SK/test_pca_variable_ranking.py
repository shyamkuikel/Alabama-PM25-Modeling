import unittest
import numpy as np
import pandas as pd
from pca_variable_ranking import VARIABLES, analyze_county


class RankingTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(42)
        self.data = pd.DataFrame(rng.normal(size=(300, 6)), columns=VARIABLES)
        self.data['Dew Point'] = self.data.Temperature + rng.normal(0, .03, 300)

    def test_covariance_reconstruction_and_full_tie(self):
        rank, variance, loading, corr, summary = analyze_county(self.data, 1)
        np.testing.assert_allclose(loading.to_numpy() @ loading.to_numpy().T, corr, atol=1e-12)
        np.testing.assert_allclose(rank.importance_percent, 100/6, atol=1e-10)
        self.assertTrue(summary['all_components_retained'])
        self.assertTrue((rank['rank'] == 1).all())
        self.assertAlmostEqual(variance.eigenvalue.sum(), 6)

    def test_constant_missing_redundancy_and_order(self):
        self.data['Precipitation'] = 0.
        self.data.loc[0, 'Precipitation'] = np.nan
        self.data.loc[1, 'Pressure'] = np.nan
        rank, _, _, _, summary = analyze_county(self.data)
        self.assertEqual(summary['complete_rows'], 299)
        self.assertEqual(rank.iloc[-1].status, 'constant')
        self.assertTrue(pd.isna(rank.iloc[-1]['rank']))
        self.assertIn('high_redundancy', rank.set_index('variable').loc['Temperature', 'status'])
        self.assertTrue(rank.importance_percent.dropna().is_monotonic_decreasing)
        self.assertAlmostEqual(rank.importance_percent.sum(), 100)

    def test_units_do_not_change_rank(self):
        original = analyze_county(self.data)[0].set_index('variable')
        self.data['Temperature'] = self.data.Temperature * 100 + 400
        changed = analyze_county(self.data)[0].set_index('variable')
        np.testing.assert_allclose(original.importance_percent, changed.importance_percent)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            analyze_county(self.data.drop(columns='Pressure'))
        with self.assertRaises(ValueError):
            analyze_county(self.data.iloc[:3])
        self.data.loc[0, 'Temperature'] = np.inf
        with self.assertRaises(ValueError):
            analyze_county(self.data)

    def test_low_representation(self):
        rank, _, _, _, _ = analyze_county(self.data, .25)
        ranked = rank.set_index('variable')
        self.assertGreater(ranked.loc['Temperature', 'communality'], .9)
        self.assertIn('low_representation', ranked.loc['Pressure', 'status'])


if __name__ == '__main__':
    unittest.main()
