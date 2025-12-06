import unittest
import pandas as pd
import numpy as np
import riskfolio as rp
from src.analytics.hrp_engine import HRPEngine

class TestHRPEngine(unittest.TestCase):
    def setUp(self):
        # Create synthetic returns data: 5 assets, 300 days
        np.random.seed(42)
        dates = pd.date_range(start="2020-01-01", periods=300, freq='D')
        
        # Correlated assets
        r1 = np.random.normal(0.001, 0.02, 300)
        r2 = r1 * 0.9 + np.random.normal(0, 0.01, 300) # Highly correlated with r1
        r3 = np.random.normal(0.0005, 0.01, 300) # Noise
        r4 = np.random.normal(0.0002, 0.03, 300)
        r5 = r4 * 0.5 + np.random.normal(0, 0.01, 300)

        data = pd.DataFrame({
            'Asset_A': r1, 'Asset_B': r2, 'Asset_C': r3,
            'Asset_D': r4, 'Asset_E': r5
        }, index=dates)
        
        self.returns = data
        self.engine = HRPEngine()
        self.engine.train(self.returns)

    def test_denoising_impact(self):
        """Test that enabling denoising produces different (hopefully better) weights."""
        # 1. Standard weights
        w_standard = self.engine.optimize(model='HRP', denoise=False)
        
        # 2. Denoised weights
        w_denoised = self.engine.optimize(model='HRP', denoise=True)
        
        # Assert they are not identical
        # (With random data, noise filtering should change the result)
        self.assertFalse(w_standard.equals(w_denoised), "Denoising should alter the weight distribution")
        
        # Check integrity
        self.assertAlmostEqual(w_denoised.sum().item(), 1.0, places=4)

    def test_gerber_statistic(self):
        """Test that using Gerber Statistic works and differs from standard Spearman."""
        # 1. Standard Spearman
        w_spearman = self.engine.optimize(model='HRP', codependence='spearman', use_gerber=False)
        
        # 2. Gerber
        # Note: 'codependence' arg might be overridden by use_gerber=True internally, 
        # or we explicitly pass 'gerber1' if the API requires that.
        # The prompt says implementation will force codependence='gerber1' if use_gerber=True.
        w_gerber = self.engine.optimize(model='HRP', use_gerber=True)
        
        self.assertFalse(w_spearman.equals(w_gerber), "Gerber statistic should produce different weights")
        self.assertAlmostEqual(w_gerber.sum().item(), 1.0, places=4)

if __name__ == '__main__':
    unittest.main()
