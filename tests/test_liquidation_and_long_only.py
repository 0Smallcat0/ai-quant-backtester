import unittest
import pandas as pd
import numpy as np
from src.backtest_engine import BacktestEngine

class TestLiquidationAndLongOnly(unittest.TestCase):
    def setUp(self):
        # Create dummy data
        dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
        self.data = pd.DataFrame({
            "Open": [100, 90, 80, 70, 60, 50, 40, 30, 20, 10],
            "Close": [95, 85, 75, 65, 55, 45, 35, 25, 15, 5],
            "High": [105, 95, 85, 75, 65, 55, 45, 35, 25, 15],
            "Low": [90, 80, 70, 60, 50, 40, 30, 20, 10, 0],
            "Volume": [1000] * 10
        }, index=dates)

    def test_liquidation_mechanism(self):
        """Test that the engine stops when equity hits zero or below."""
        # Initial capital small enough to go bust quickly
        engine = BacktestEngine(initial_capital=10000, long_only=True, slippage=0.0, min_commission=0.0, commission_rate=0.0)
        engine.set_position_sizing("fixed_percent", target=1.0)
        
        # Signal to BUY at the beginning
        signals = pd.Series(0, index=self.data.index)
        signals.iloc[0] = 1 # Buy on day 1
        
        # The price drops significantly every day. 
        # Day 1 Open: 100. Buy 1 share (approx).
        # Day 1 Close: 95. Equity = 95.
        # ...
        # Eventually it should drop enough to bust if we had leverage, 
        # but with 1 share and price > 0 it won't bust unless price goes to 0.
        # Let's force a bust by setting price to 0 or negative (if possible in data)
        # or by using leverage/commission if supported.
        # Since we don't have explicit leverage, let's simulate a massive drop.
        
        dates_bust = pd.date_range(start="2023-01-01", periods=5, freq="D")
        data_bust = pd.DataFrame({
            "Open": [100, 100, 50, 0, 0],
            "Close": [100, 50, 0, -50, -100], # Artificial drop to negative to force check
            "High": [100]*5, "Low": [100]*5, "Volume": [1000]*5
        }, index=dates_bust)
        
        signals_bust = pd.Series(0, index=dates_bust)
        signals_bust.iloc[0] = 1 # Buy
        signals_bust = signals_bust.replace(0, np.nan).ffill().fillna(0)
        
        engine.run(data_bust, signals_bust)
        
        equity_curve = pd.DataFrame(engine.equity_curve)
        
        # Check if equity hit 0
        final_equity = equity_curve['equity'].iloc[-1]
        self.assertAlmostEqual(final_equity, 0, places=6, msg="Equity should be 0 after liquidation")
        
        # Check if it stopped correctly (equity should be 0 from the point of bust onwards)
        # In this data, Close becomes 0 on index 2.
        # So equity should be 0 on index 2.
        self.assertAlmostEqual(equity_curve['equity'].iloc[2], 0, places=6, msg="Equity should be 0 when price hits 0")

    def test_long_only_enforcement(self):
        """Test that short signals are ignored in long_only mode."""
        engine = BacktestEngine(initial_capital=10000, long_only=True)
        
        # Signal to SELL (Short) without holding a position
        signals = pd.Series(0, index=self.data.index)
        signals.iloc[0] = -1 # Sell/Short
        
        engine.run(self.data, signals)
        
        # Should have NO trades
        self.assertEqual(len(engine.trades), 0, "Should not execute short trades in long_only mode")
        
        # Equity should remain initial capital (flat)
        final_equity = engine.equity_curve.iloc[-1]['equity']
        self.assertEqual(final_equity, 10000, "Equity should not change if no trades are made")

    def test_short_allowed_when_disabled(self):
        """Test that shorting IS allowed when long_only=False."""
        engine = BacktestEngine(initial_capital=10000, long_only=False)
        
        # Signal to SELL (Short)
        signals = pd.Series(0, index=self.data.index)
        signals.iloc[0] = -1 # Sell/Short
        
        engine.run(self.data, signals)
        
        # Should have 1 trade (Short entry)
        self.assertGreater(len(engine.trades), 0, "Should execute short trade when long_only=False")
        self.assertEqual(engine.trades[0].type, "SELL", "First trade should be SELL")

if __name__ == '__main__':
    unittest.main()
