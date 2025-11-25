import unittest
import pandas as pd
import numpy as np
from src.backtest_engine import BacktestEngine

class TestAdvancedLogic(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range(start='2023-01-01', periods=10)
        self.df = pd.DataFrame({
            'Open': [100] * 10,
            'High': [105] * 10,
            'Low': [95] * 10,
            'Close': [100] * 10,
            'Volume': [1000] * 10
        }, index=dates)
        # Note: BacktestEngine expects Capitalized columns in some places (row["Open"]) but lowercase in others?
        # Let's check BacktestEngine again. It uses row["Open"], row["Close"].
        # My previous setUp used lowercase. I should fix that too.

    def test_long_only(self):
        """Test Long Only mode ignores Short signals."""
        # Initialize with long_only=True
        engine = BacktestEngine(initial_capital=10000, long_only=True)
        
        signals = pd.Series(0, index=self.df.index)
        signals.iloc[0] = -1 # Sell Short
        
        engine.run(self.df, signals)
        
        self.assertEqual(len(engine.trades), 0)

    def test_trade_object_access(self):
        """Test that trades are stored as objects and accessible."""
        engine = BacktestEngine(initial_capital=10000, slippage=0.0, commission_rate=0.0, min_commission=0.0)
        signals = pd.Series(0, index=self.df.index)
        signals.iloc[0] = 1 # Buy
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        
        engine.run(self.df, signals)
        
        # Should have 1 trade (Buy)
        self.assertEqual(len(engine.trades), 1)
        trade = engine.trades[0]
        self.assertEqual(trade.type, 'BUY')
        self.assertEqual(trade.entry_price, 100)

if __name__ == '__main__':
    unittest.main()
