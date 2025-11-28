import pytest
import pandas as pd
import numpy as np
from src.strategies.loader import StrategyLoader, StrategyLoadError
from src.strategies.manager import StrategyManager
from src.strategies.presets import SentimentRSIStrategy, MovingAverageStrategy, BollingerBreakoutStrategy

class TestStrategySafety:
    def setup_method(self):
        self.loader = StrategyLoader()
        self.manager = StrategyManager(filepath="tests/temp_strategies.json")

    def teardown_method(self):
        import os
        if os.path.exists("tests/temp_strategies.json"):
            os.remove("tests/temp_strategies.json")
        if os.path.exists("tests/temp_strategies.json.tmp"):
            os.remove("tests/temp_strategies.json.tmp")

    def test_advanced_lookahead_detection(self):
        """Case A: Detect advanced lookahead patterns like slicing and future indexing."""
        
        # 1. Slicing Lookahead
        malicious_code_slice = """
from src.strategies.base import Strategy
import pandas as pd

class MaliciousSlice(Strategy):
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        # Look ahead by slicing from current to end
        future = df.iloc[10:] 
        df['signal'] = 0
        return df
"""
        with pytest.raises(StrategyLoadError, match="Security Violation"):
            self.loader.load_from_code(malicious_code_slice)

        # 2. Shift Lookahead (Negative)
        malicious_code_shift = """
from src.strategies.base import Strategy
import pandas as pd

class MaliciousShift(Strategy):
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        # Look ahead using negative shift
        df['future_close'] = df['close'].shift(-2)
        df['signal'] = 0
        return df
"""
        with pytest.raises(StrategyLoadError, match="Security Violation"):
            self.loader.load_from_code(malicious_code_shift)

        # 3. Future Indexing
        malicious_code_index = """
from src.strategies.base import Strategy
import pandas as pd

class MaliciousIndex(Strategy):
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        for i in range(len(df)):
            # Access future index
            future_val = df.iloc[i + 5]
        df['signal'] = 0
        return df
"""
        with pytest.raises(StrategyLoadError, match="Security Violation"):
            self.loader.load_from_code(malicious_code_index)

    def test_input_validation(self):
        """Case B: Validate strategy name length and code size."""
        
        # 1. Name too long
        long_name = "a" * 101
        with pytest.raises(ValueError, match="Strategy name must be 1-100 characters"):
            self.manager.save(long_name, "valid code")

        # 2. Code too large
        large_code = "a" * 1_000_001
        with pytest.raises(ValueError, match="Strategy code exceeds size limit"):
            self.manager.save("valid_name", large_code)

    def test_preset_robustness_nan_handling(self):
        """Case C: Ensure presets handle NaNs correctly and don't return NaNs."""
        
        # Create data with NaNs (insufficient history for indicators)
        data = pd.DataFrame({
            'open': [100.0] * 5,
            'high': [105.0] * 5,
            'low': [95.0] * 5,
            'close': [100.0] * 5,
            'volume': [1000] * 5
        })
        # MA window 10 > len 5 -> will produce NaNs
        
        # Test MA
        ma_strategy = MovingAverageStrategy(window=10)
        signals_ma = ma_strategy.generate_signals(data)
        assert not signals_ma['signal'].isnull().any(), "MA Strategy returned NaNs in signal"
        
        # Test RSI
        # RSI period 14 > len 5
        rsi_strategy = SentimentRSIStrategy(period=14)
        signals_rsi = rsi_strategy.generate_signals(data)
        assert not signals_rsi['signal'].isnull().any(), "RSI Strategy returned NaNs in signal"
        
        # Test Bollinger
        # Window 20 > len 5
        bb_strategy = BollingerBreakoutStrategy(window=20)
        signals_bb = bb_strategy.generate_signals(data)
        assert not signals_bb['signal'].isnull().any(), "Bollinger Strategy returned NaNs in signal"
