import pytest
import pandas as pd
from src.strategies.loader import StrategyLoader, StrategyLoadError
from src.strategies.base import Strategy

class TestStrategyLoaderFix:
    def setup_method(self):
        self.loader = StrategyLoader()

    def test_load_valid_strategy_with_whitespace(self):
        """
        Test that a valid strategy with normal whitespace and indentation loads correctly.
        The current buggy loader removes all whitespace, causing this to fail with SyntaxError.
        """
        code = """
from src.strategies.base import Strategy
import pandas as pd

class ValidStrategy(Strategy):
    def __init__(self, params=None):
        self.params = params or {}

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df['signal'] = 0
        return df
"""
        # This should succeed with the fix, but fail currently
        try:
            strategy = self.loader.load_from_code(code)
            assert isinstance(strategy, Strategy)
            assert hasattr(strategy, 'generate_signals')
        except StrategyLoadError as e:
            pytest.fail(f"Failed to load valid strategy: {e}")

    def test_security_lookahead_bias_with_spaces(self):
        """
        Test that look-ahead bias patterns with spaces are detected.
        e.g. 'shift( -1 )'
        """
        code = """
from src.strategies.base import Strategy
import pandas as pd

class CheatingStrategy(Strategy):
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        # Malicious space insertion to bypass simple substring check
        df['close'].shift( -1 )
        return df
"""
        with pytest.raises(StrategyLoadError, match="Security Violation"):
            self.loader.load_from_code(code)

    def test_security_iloc_forward_look_with_spaces(self):
        """
        Test that iloc forward look patterns with spaces are detected.
        e.g. 'iloc[ i + 1 ]'
        """
        code = """
from src.strategies.base import Strategy
import pandas as pd

class CheatingStrategyIloc(Strategy):
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        for i in range(len(df)):
            # Malicious space insertion
            val = df.iloc[ i + 1 ]
        return df
"""
        with pytest.raises(StrategyLoadError, match="Security Violation"):
            self.loader.load_from_code(code)

    def test_missing_generate_signals(self):
        """
        Test that a strategy class without generate_signals raises an error.
        """
        code = """
from src.strategies.base import Strategy
import pandas as pd

class IncompleteStrategy(Strategy):
    def __init__(self, params=None):
        pass
    # Missing generate_signals
"""
        # This might fail instantiation or validation depending on implementation
        # We want to ensure it's caught
        with pytest.raises((StrategyLoadError, TypeError)):
             self.loader.load_from_code(code)
