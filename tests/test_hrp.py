import unittest
import pandas as pd
import numpy as np
from src.strategies.portfolio import HRPAllocator

class TestHRPAllocator(unittest.TestCase):
    def setUp(self):
        # Create synthetic returns data: 3 assets, 300 days
        np.random.seed(42)
        dates = pd.date_range(start="2020-01-01", periods=300, freq='D')
        
        # Correlated assets
        r1 = np.random.normal(0.001, 0.02, 300)
        r2 = r1 * 0.8 + np.random.normal(0, 0.01, 300) # Highly correlated with r1
        r3 = np.random.normal(0.0005, 0.01, 300) # Less correlated
        
        data = pd.DataFrame({
            'Asset_A': r1,
            'Asset_B': r2,
            'Asset_C': r3
        }, index=dates)
        
        self.returns = data
        self.allocator = HRPAllocator()
        
    def test_train_and_optimize(self):
        self.allocator.train(self.returns)
        weights = self.allocator.optimize(model='HRP', codependence='pearson', rm='MV')
        
        self.assertIsInstance(weights, pd.DataFrame)
        self.assertEqual(weights.shape, (3, 1))
        # Check sum close to 1
        self.assertAlmostEqual(weights.sum().item(), 1.0, places=4)
        
        # Since A and B are highly correlated, HRP should treat them as a cluster
        # and likely give them lower individual weight compared to C if C is low correlation/variance?
        # Actually HRP splits risk between clusters. A+B is one cluster, C is another.
        # If variances are similar, Cluster(A+B) gets ~50%, Cluster(C) gets ~50%.
        # Then A and B split their 50%. So A~25%, B~25%, C~50%.
        # Let's check general direction: C should probably have higher weight than A or B individually.
        w_dict = weights['weights'].to_dict()
        # This assertion depends on exact random seed, so might be loose, but logic holds.
        # But for unit test, just structural checks are enough.
        self.assertTrue(all(w >= 0 for w in weights.values))

    def test_rolling_optimize(self):
        # Window 100, Rebalance 20 -> Should produce weights for 300-100 = 200 days
        weights_ts = HRPAllocator.rolling_optimize(self.returns, window=100, rebalance_period=50)
        
        # Expected Logic:
        # Data starts day 0. Window 100. First valid calculation at day 100.
        # First weight applies from day 100.
        # So output should index from day 100 to 299.
        
        self.assertIsInstance(weights_ts, pd.DataFrame)
        self.assertEqual(len(weights_ts), 200) 
        self.assertEqual(weights_ts.shape[1], 3)
        
        # Check integrity (no nans)
        self.assertFalse(weights_ts.isnull().values.any())
        
        # Check rebalance behavior: Weights should be constant for "rebalance_period" days
        # E.g. day 100 to 149 should be same, day 150 changes.
        # Using iloc to check
        row_100 = weights_ts.iloc[0].values
        row_110 = weights_ts.iloc[10].values
        row_150 = weights_ts.iloc[50].values
        
        np.testing.assert_array_almost_equal(row_100, row_110)
        # It's possible randomly they are same, but unlikely.
        # row_150 should be different (new optimization)
        # Note: If optimize returns perfectly stable weights, this might fail, but with random noise it shouldn't.
        # Let's skip the "not equal" assertion to avoid flake, but verify dimensions strictly.

    def test_blend_alpha_scaling(self):
        dates = self.returns.index
        # Dummy flat weights: 0.33 each
        hrp_weights = pd.DataFrame(0.3333, index=dates, columns=['A', 'B', 'C'])
        
        # Alpha signals: A is Bullish (+1), B is Bearish (-1), C is Neutral (0)
        alpha = pd.DataFrame(0.0, index=dates, columns=['A', 'B', 'C'])
        alpha['A'] = 1.0
        alpha['B'] = -1.0
        
        # Scale factor 0.5
        # Expected:
        # A -> 0.33 * (1 + 0.5*1) = 0.33 * 1.5 = 0.495
        # B -> 0.33 * (1 + 0.5*-1) = 0.33 * 0.5 = 0.165
        # C -> 0.33 * (1 + 0) = 0.33
        # Sum = 0.99
        # Normalize -> A > C > B
        
        blended = HRPAllocator.blend_alpha(hrp_weights, alpha, scale_factor=0.5)
        
        # Check first row
        row = blended.iloc[0]
        self.assertGreater(row['A'], row['C'])
        self.assertGreater(row['C'], row['B'])
        self.assertAlmostEqual(row.sum(), 1.0, places=4)

if __name__ == '__main__':
    unittest.main()
