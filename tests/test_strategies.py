import pytest
import pandas as pd
import numpy as np
import io
import sys
from unittest.mock import MagicMock, patch

from src.strategies.base import Strategy
from src.strategies.macd_strategy import MACDStrategy
from src.strategies.presets import MovingAverageStrategy, SentimentRSIStrategy, BollingerBreakoutStrategy
from src.strategies.loader import StrategyLoader, StrategyLoadError

class TestBaseStrategy:
    def test_convert_to_signal(self):
        df = pd.DataFrame({
            'entries': [False, True, False, False],
            'exits': [False, False, True, False]
        })
        strategy = MovingAverageStrategy() # Just use a concrete class to access the method
        res = strategy.convert_to_signal(df)
        assert 'signal' in res.columns
        assert res['signal'].tolist() == [0, 1, -1, 0]

    def test_convert_to_signal_no_entries(self):
        df = pd.DataFrame({'close': [1, 2, 3]})
        strategy = MovingAverageStrategy()
        res = strategy.convert_to_signal(df)
        assert 'signal' in res.columns
        assert (res['signal'] == 0).all()

class TestMACDStrategy:
    def test_generate_signals(self):
        # Create dummy data where MACD crossover happens
        # Fast=12, Slow=26.
        # We need enough data.
        dates = pd.date_range(start='2020-01-01', periods=100)
        # Create a price series that goes up then down
        prices = [100 + i*1 for i in range(50)] + [150 - i*1 for i in range(50)]
        df = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = MACDStrategy()
        res = strategy.generate_signals(df)
        
        assert 'entries' in res.columns
        assert 'exits' in res.columns
        assert 'signal' in res.columns
        assert 'macd' in res.columns
        assert 'signal_line' in res.columns

class TestPresets:
    def test_moving_average_strategy(self):
        dates = pd.date_range(start='2020-01-01', periods=20)
        prices = [10] * 10 + [20] * 10 
        # MA(Window=5). 
        # When price jumps to 20, MA will lag. Price > MA -> Entry.
        df = pd.DataFrame({'close': prices}, index=dates)
        strategy = MovingAverageStrategy(window=5)
        res = strategy.generate_signals(df)
        
        assert 'entries' in res.columns
        assert 'signal' in res.columns
        # Check last point: Price 20, MA should be 20 eventually, but safe_rolling shifts by 1.
        # At index 19: Price is 20. Prev 5 prices are 20. MA(5) of prev is 20. Close > MA? No, 20 !> 20.
        # At index 10: Price is 20. Prev 5 prices are 10. MA is 10. 20 > 10 -> Buy.
        # Let's check index 10.
        assert res.iloc[10]['signal'] == 1 # Buy

    def test_sentiment_rsi_strategy(self):
        dates = pd.date_range(start='2020-01-01', periods=100)
        df = pd.DataFrame({
            'close': np.random.randn(100).cumsum() + 100, 
            'sentiment': [0.5] * 100
        }, index=dates)
        strategy = SentimentRSIStrategy()
        res = strategy.generate_signals(df)
        
        assert 'entries' in res.columns
        assert 'signal' in res.columns
        assert 'target_size' in res.columns

class TestLoaderValidation:
    def test_relative_import_warning(self):
        loader = StrategyLoader()
        code = """
from .base import Strategy
import pandas as pd
class MyStrat(Strategy):
    def generate_signals(self, df): return df
"""
        # Capture stdout
        captured = io.StringIO()
        sys.stdout = captured
        try:
            loader.load_from_code(code)
        except Exception:
            pass # We expect failure/warning, likely failure due to import not finding module in test
        
        sys.stdout = sys.__stdout__
        output = captured.getvalue()
        assert "Relative import detected" in output

    def test_matplotlib_warning(self):
        loader = StrategyLoader()
        code = """
from src.strategies.base import Strategy
import matplotlib.pyplot as plt
class MyStrat(Strategy):
    def generate_signals(self, df): return df
"""
        captured = io.StringIO()
        sys.stdout = captured
        try:
            loader.load_from_code(code)
        except Exception:
            pass
        sys.stdout = sys.__stdout__
        output = captured.getvalue()
        assert "Visual library 'matplotlib' detected" in output
