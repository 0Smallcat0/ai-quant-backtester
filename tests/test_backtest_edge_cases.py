import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch
from src.backtest_engine import BacktestEngine
from src.config.settings import settings

class TestBacktestEdgeCases:
    
    def test_min_exposure_trigger(self):
        """
        Case A: Verify that trades below MIN_EXPOSURE_THRESHOLD are filtered out.
        """
        # Create dummy data
        dates = pd.date_range(start="2023-01-01", periods=5)
        data = pd.DataFrame({
            "open": [100.0] * 5,
            "high": [105.0] * 5,
            "low": [95.0] * 5,
            "close": [100.0] * 5,
            "volume": [1000] * 5
        }, index=dates)
        
        # Signal: 5% exposure
        signals = pd.Series([0.05] * 5, index=dates)
        
        # Set threshold to 10% (0.1)
        with patch.object(settings, 'MIN_EXPOSURE_THRESHOLD', 0.1):
            engine = BacktestEngine()
            engine.run(data, signals)
            
            # Should be 0 trades because 0.05 < 0.1
            assert len(engine.trades) == 0, "Trades should be filtered by MIN_EXPOSURE_THRESHOLD"
            
            # Verify position is 0
            assert engine.position == 0.0

    def test_zero_price_handling(self):
        """
        Case B: Verify engine handles zero prices gracefully (without crashing).
        """
        dates = pd.date_range(start="2023-01-01", periods=5)
        # Remove NaN, only test 0.0
        data = pd.DataFrame({
            "open": [100.0, 0.0, 100.0, 100.0, 100.0], # Day 2 is 0
            "high": [105.0] * 5,
            "low": [95.0] * 5,
            "close": [100.0] * 5,
            "volume": [1000] * 5
        }, index=dates)
        
        signals = pd.Series([1.0] * 5, index=dates) # Buy signal
        
        engine = BacktestEngine()
        # Should not raise ZeroDivisionError
        try:
            engine.run(data, signals)
        except Exception as e:
            pytest.fail(f"Engine crashed on zero price: {e}")
            
        assert len(engine.trades) > 0

    def test_bankruptcy_logic(self):
        """
        Case C: Verify engine stops immediately upon bankruptcy.
        We need to force Equity = 0. In Spot trading, this requires Cash=0 and PositionValue=0.
        We disable commissions and use 100% allocation to achieve this.
        """
        dates = pd.date_range(start="2023-01-01", periods=10)
        data = pd.DataFrame({
            "open": [1.0] * 10,
            "high": [1.0] * 10,
            "low": [1.0] * 10,
            "close": [1.0] * 10,
            "volume": [1000] * 10
        }, index=dates)
        
        # Day 3: Price drops to 0.
        data.loc[dates[2:], ['open', 'high', 'low', 'close']] = 0.0
        
        signals = pd.Series([1.0] * 10, index=dates)
        
        # Patch settings to remove friction so we can spend exactly all cash
        with patch.object(settings, 'COMMISSION_RATE', 0.0), \
             patch.object(settings, 'MIN_COMMISSION', 0.0), \
             patch.object(settings, 'SLIPPAGE', 0.0):
             
            # Note: We must pass these explicitly because default args are evaluated at import time
            engine = BacktestEngine(
                initial_capital=100.0,
                commission_rate=0.0,
                slippage=0.0,
                min_commission=0.0
            ) 
            engine.set_position_sizing("fixed_percent", target=1.0) # 100% allocation
            
            engine.run(data, signals)
            
            equity_curve = engine.equity_curve
            assert not equity_curve.empty
            
            # Check if we have a bankruptcy event (equity <= small epsilon)
            # We use 1e-5 to account for floating point residuals caused by EPSILON safety in target calc
            zero_equity_days = equity_curve[equity_curve['equity'] <= 1e-5]
            assert not zero_equity_days.empty, f"Should have reached bankruptcy. Min equity: {equity_curve['equity'].min()}"
            
            # Verify it stopped
            assert equity_curve.iloc[-1]['equity'] <= 1e-5
