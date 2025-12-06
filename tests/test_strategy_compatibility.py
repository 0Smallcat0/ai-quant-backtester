
import pytest
import pandas as pd
from src.strategies.base import Strategy
from src.strategies.loader import StrategyLoader

# Mock Strategy Classes
class StandardStrategy(Strategy):
    def __init__(self, params=None):
        super().__init__(params)
        self.period = self.params.get('period', 14)

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        return data

class LegacyStrategy(Strategy):
    def __init__(self, window=10, threshold=30):
        super().__init__()
        self.window = window
        self.threshold = threshold

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        return data

class TestStrategyCompatibility:
    def setup_method(self):
        self.loader = StrategyLoader()

    def test_load_strategy_with_params_dict(self):
        """Test Case 1: Standard strategy with init(self, params=None)"""
        # We need to simulate loading this class.
        # Since StrategyLoader.load_from_code normally processes string code, 
        # but the core fix is in the instantiation logic which we can test by 
        # refactoring logic or mocking the class discovery.
        # However, to test the loader logic properly, let's create a code string that defines the class.
        
        code = """
from src.strategies.base import Strategy
import pandas as pd

class VerifiedStandardStrategy(Strategy):
    def __init__(self, params=None):
        super().__init__(params)
        self.period = self.params.get('period', 14)

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        return data
        """
        
        strategy = self.loader.load_from_code(code)
        assert isinstance(strategy, Strategy)
        # Default param
        # Fix: Check the instance attribute, not the params dict (which is empty)
        assert strategy.period == 14

    def test_load_legacy_strategy_named_args_via_code(self):
        """Test Case 2: Legacy strategy with init(self, window=10) via code string"""
        code = """
from src.strategies.base import Strategy
import pandas as pd

class VerifiedLegacyStrategy(Strategy):
    def __init__(self, window=10, threshold=30):
        super().__init__()
        self.window = window
        self.threshold = threshold

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        return data
        """
        
        # This TEST is expected to FAIL until we fix loader.py
        # StrategyLoader currently tries to inject params={} which will fail for named args without defaults or correct matching.
        # Wait, the legacy strategy DEFINES defaults, so calling with empty dict might fail if it passes 'params' as a kwarg that isn't expected?
        # Actually current loader does: strategy_class(params={})
        # If __init__ is (self, window=10), calling with params={} raises TypeError: got an unexpected keyword argument 'params'
        
        try:
            strategy = self.loader.load_from_code(code)
            assert strategy.window == 10
        except Exception as e:
            pytest.fail(f"Legacy strategy loading failed: {e}")

