import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch
from src.backtest_engine import BacktestEngine
from src.config.settings import settings

class TestSSOTCompliance:
    
    def test_backtest_engine_defaults(self):
        """
        Case A: Verify BacktestEngine uses settings.INITIAL_CAPITAL by default.
        """
        engine = BacktestEngine()
        assert engine.initial_capital == settings.INITIAL_CAPITAL
        assert engine.current_capital == settings.INITIAL_CAPITAL

    def test_min_exposure_threshold_ssot(self):
        """
        Case B: Verify BacktestEngine uses settings.MIN_EXPOSURE_THRESHOLD.
        We verify this by monkeypatching the setting to a high value and ensuring trades are filtered.
        """
        # Create dummy data
        dates = pd.date_range(start="2023-01-01", periods=5)
        data = pd.DataFrame({
            "open": [100.0, 101.0, 102.0, 103.0, 104.0],
            "high": [105.0, 106.0, 107.0, 108.0, 109.0],
            "low": [95.0, 96.0, 97.0, 98.0, 99.0],
            "close": [101.0, 102.0, 103.0, 104.0, 105.0],
            "volume": [1000, 1000, 1000, 1000, 1000]
        }, index=dates)
        
        # Create signals: 10% exposure
        # If threshold is 0.001 (default), this should trade.
        # If we raise threshold to 0.2 (20%), this should NOT trade.
        signals = pd.Series([0.1, 0.1, 0.1, 0.1, 0.1], index=dates)
        
        # 1. Verify it trades with default settings (0.001)
        # Note: The hardcoded value in backtest_engine.py is 0.001, which matches settings.
        # So this pass confirms baseline behavior.
        engine = BacktestEngine()
        engine.run(data, signals)
        assert len(engine.trades) > 0, "Should trade with default threshold (0.1 > 0.001)"
        
        # 2. Verify it respects the SETTING when changed
        # We patch the settings object. 
        # Since the code imports 'settings' instance, we patch attributes on it.
        with patch.object(settings, 'MIN_EXPOSURE_THRESHOLD', 0.2):
            engine_high_thresh = BacktestEngine()
            engine_high_thresh.run(data, signals)
            
            # If the code uses hardcoded 0.001, it will still trade (0.1 > 0.001).
            # If the code uses settings.MIN_EXPOSURE_THRESHOLD (0.2), it will NOT trade (0.1 < 0.2).
            assert len(engine_high_thresh.trades) == 0, "Should NOT trade when threshold is raised to 0.2 via settings"
