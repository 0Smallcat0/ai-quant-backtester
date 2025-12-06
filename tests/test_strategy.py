import unittest
import pandas as pd
import numpy as np
from src.strategies.presets import MovingAverageStrategy

class TestStrategy(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range(start='2023-01-01', periods=50)
        # Create a trend: Price goes up then down
        prices = list(range(100, 125)) + list(range(125, 100, -1))
        self.df = pd.DataFrame({
            'close': prices,
            'open': prices, 
            'high': prices,
            'low': prices,
            'volume': 1000
        }, index=dates)

    def test_ma_strategy_output(self):
        """Test that the strategy returns a valid signal series."""
        # MovingAverageStrategy: Buy when Price > MA, Sell when Price < MA
        strategy = MovingAverageStrategy(window=10)
        signals_df = strategy.generate_signals(self.df)
        
        self.assertIsInstance(signals_df, pd.DataFrame)
        self.assertIn('signal', signals_df.columns)
        self.assertEqual(len(signals_df), len(self.df))
        
        signals = signals_df['signal']
        
        # Check values are in {-1, 0, 1}
        unique_values = signals.unique()
        for val in unique_values:
            self.assertIn(val, [-1, 0, 1])
            
        # Check logic:
        # Index 20: Price is 120. 
        # MA(10) of [111..120] is 115.5
        # Price (120) > MA (115.5) -> Signal 1 (Buy)
        self.assertEqual(signals.iloc[20], 1)

if __name__ == '__main__':
    unittest.main()
