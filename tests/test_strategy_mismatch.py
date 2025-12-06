import pytest
import os
import sys
from src.strategies.loader import StrategyLoader, StrategyLoadError
from src.strategies.base import Strategy
import pandas as pd

# Define a temporary strategy file content with mismatched name
# File: temp_mismatch.py
# Class: TempMismatchStrategy
TEMP_FILENAME = "temp_mismatch.py"
TEMP_CODE = """
from src.strategies.base import Strategy
import pandas as pd

class TempMismatchStrategy(Strategy):
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        data['signal'] = 0
        return data[['signal']]
"""

@pytest.fixture
def temp_mismatch_file():
    """Creates a temporary strategy file in src/strategies/ and removes it after test."""
    strategies_dir = os.path.join(os.path.dirname(__file__), '..', 'src', 'strategies')
    file_path = os.path.join(strategies_dir, TEMP_FILENAME)
    
    with open(file_path, 'w') as f:
        f.write(TEMP_CODE)
        
    yield file_path
    
    if os.path.exists(file_path):
        os.remove(file_path)

def test_snake_input_camel_class(temp_mismatch_file):
    """
    Case A: Verify that loader finds 'TempMismatchStrategy' class 
    when searching for 'temp_mismatch' (filename match).
    """
    loader = StrategyLoader()
    
    # Input is snake_case (matching filename), but class is CamelCase
    # The current implementation (before fix) might try to find 'temp_mismatch' class or fail.
    # We want it to find the Strategy subclass inside.
    
    strategy_name = "temp_mismatch"
    strategy_class = loader.load_strategy(strategy_name)
    
    assert strategy_class is not None
    assert strategy_class.__name__ == "TempMismatchStrategy"
    assert issubclass(strategy_class, Strategy)
