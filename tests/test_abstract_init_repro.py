import pytest
from src.strategies.base import Strategy
from src.strategies.presets import SentimentRSIStrategy
import pandas as pd

class TestAbstractInitRepro:
    def test_preset_instantiation(self):
        """
        Test if existing presets can be instantiated.
        """
        try:
            strategy = SentimentRSIStrategy()
            assert isinstance(strategy, Strategy)
        except TypeError as e:
            pytest.fail(f"Failed to instantiate SentimentRSIStrategy: {e}")

    def test_dynamic_strategy_without_init(self):
        """
        Test if a strategy without __init__ raises TypeError.
        This simulates the AI generated code which might skip __init__.
        """
        class GeneratedStrategy(Strategy):
            def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
                return data

        # This should now succeed
        try:
            strategy = GeneratedStrategy()
            assert isinstance(strategy, Strategy)
        except TypeError as e:
            pytest.fail(f"Failed to instantiate GeneratedStrategy: {e}")
