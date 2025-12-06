
import pytest
from src.strategies.loader import StrategyLoader, StrategyLoadError

class TestSecurityShift:
    def setup_method(self):
        self.loader = StrategyLoader()

    def test_shift_positive_allowed(self):
        """Case 1: valid shift(1) should pass"""
        code = """
from src.strategies.base import Strategy
import pandas as pd

class PositiveShiftStrategy(Strategy):
    def __init__(self, params=None):
        super().__init__(params)

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        data['prev_close'] = data['close'].shift(1)
        data['signal'] = 0
        return data
        """
        try:
            self.loader.load_from_code(code)
        except StrategyLoadError as e:
            pytest.fail(f"Positive shift(1) was incorrectly flagged as security violation: {e}")

    def test_shift_negative_forbidden(self):
        """Case 2: invalid shift(-1) should fail"""
        code = """
from src.strategies.base import Strategy
import pandas as pd

class NegativeShiftStrategy(Strategy):
    def __init__(self, params=None):
        super().__init__(params)

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        # FUTURE LEAK
        data['future_close'] = data['close'].shift(-1) 
        data['signal'] = 0
        return data
        """
        with pytest.raises(StrategyLoadError) as excinfo:
            self.loader.load_from_code(code)
        
        assert "Security Violation" in str(excinfo.value)
