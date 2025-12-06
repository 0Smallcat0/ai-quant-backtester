import pytest
import os
import sys
from src.strategies.loader import StrategyLoader, StrategyLoadError
from src.strategies.base import Strategy
import pandas as pd

# Define a temporary strategy file content
TEMP_STRAT_NAME = "TempAutoStrat"
TEMP_STRAT_FILENAME = "temp_auto_strat.py"
TEMP_STRAT_CODE = """
from src.strategies.base import Strategy
import pandas as pd

class TempAutoStrat(Strategy):
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        data['signal'] = 0
        return data[['signal']]
"""

@pytest.fixture
def temp_strategy_file():
    """Creates a temporary strategy file in src/strategies/ and removes it after test."""
    strategies_dir = os.path.join(os.path.dirname(__file__), '..', 'src', 'strategies')
    file_path = os.path.join(strategies_dir, TEMP_STRAT_FILENAME)
    
    with open(file_path, 'w') as f:
        f.write(TEMP_STRAT_CODE)
        
    yield file_path
    
    if os.path.exists(file_path):
        os.remove(file_path)

def test_auto_discovery(temp_strategy_file):
    """
    Case A: Verify that StrategyLoader can dynamically discover and load a strategy file
    based on the strategy name (CamelCase -> snake_case).
    """
    loader = StrategyLoader()
    
    # Attempt to load the strategy by name
    # Note: We expect load_strategy to return the CLASS, not an instance, 
    # or an instance if that's what the contract will be.
    # Based on run_backtest.py usage: strategy_class = loader.load_strategy(...)
    # So it should return a class.
    
    try:
        strategy_class = loader.load_strategy(TEMP_STRAT_NAME)
    except AttributeError:
        pytest.fail("StrategyLoader does not have 'load_strategy' method yet.")
    except StrategyLoadError:
        pytest.fail(f"Failed to load strategy '{TEMP_STRAT_NAME}' dynamically.")
        
    assert strategy_class is not None
    assert strategy_class.__name__ == TEMP_STRAT_NAME
    assert issubclass(strategy_class, Strategy)
    
    # Verify instantiation
    instance = strategy_class()
    assert isinstance(instance, Strategy)
    assert hasattr(instance, 'generate_signals')

def test_discovery_failure():
    """Verify that it raises StrategyLoadError for non-existent strategies."""
    loader = StrategyLoader()
    with pytest.raises(StrategyLoadError):
        loader.load_strategy("NonExistentStrategy")
