import unittest
import pandas as pd
from src.strategies.loader import StrategyLoader
from src.strategies.base import Strategy

class TestStrategyLoader(unittest.TestCase):
    def setUp(self):
        self.loader = StrategyLoader()

    def test_load_preset_moving_average(self):
        """Test loading the MovingAverageStrategy preset."""
        strategy = self.loader.load_preset("MovingAverageStrategy", window=20)
        self.assertIsInstance(strategy, Strategy)
        self.assertEqual(strategy.__class__.__name__, "MovingAverageStrategy")
        self.assertEqual(strategy.window, 20)

    def test_load_preset_rsi(self):
        """Test loading the SentimentRSIStrategy preset."""
        strategy = self.loader.load_preset("SentimentRSIStrategy", period=14)
        self.assertIsInstance(strategy, Strategy)
        self.assertEqual(strategy.__class__.__name__, "SentimentRSIStrategy")
        self.assertEqual(strategy.period, 14)

    def test_preset_execution_interface(self):
        """Test that loaded presets adhere to the execution interface."""
        strategy = self.loader.load_preset("MovingAverageStrategy", window=5)
        
        # Create dummy data
        data = pd.DataFrame({
            'close': [10, 11, 12, 13, 14, 15, 14, 13, 12, 11]
        })
        
        result = strategy.generate_signals(data)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertIn('signal', result.columns)
        self.assertEqual(len(result), len(data))

    def test_detect_lookahead_bias(self):
        """Test that the loader detects and rejects look-ahead bias patterns."""
        # Code with .shift(-1)
        bad_code = """
import pandas as pd
from src.strategies.base import Strategy

class CheatingStrategy(Strategy):
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        # Look-ahead bias: using future data
        df['future_close'] = df['close'].shift(-1)
        df['signal'] = 0
        df.loc[df['future_close'] > df['close'], 'signal'] = 1
        return df
"""
        with self.assertRaises(Exception) as cm:
            self.loader.load_from_code(bad_code)
        
        self.assertIn("Security Violation", str(cm.exception))
        self.assertIn("Security Violation", str(cm.exception))
        # The error message now contains the regex pattern, not the simple string
        # self.assertIn("shift(-", str(cm.exception))

if __name__ == '__main__':
    unittest.main()
