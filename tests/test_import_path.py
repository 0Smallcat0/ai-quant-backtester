import pytest
import os
import sys
from src.strategies.loader import StrategyLoader
from src.strategies.base import Strategy
import pandas as pd

# Define a temporary strategy file content that uses 'from strategies.base import Strategy'
# This requires 'src' to be in sys.path
TEMP_FILENAME = "temp_import_test.py"
TEMP_CODE = """
# This import style requires 'src' directory to be in sys.path
from strategies.base import Strategy
import pandas as pd

class TempImportStrategy(Strategy):
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        data['signal'] = 0
        return data[['signal']]
"""

@pytest.fixture
def temp_import_file():
    """Creates a temporary strategy file in src/strategies/ and removes it after test."""
    strategies_dir = os.path.join(os.path.dirname(__file__), '..', 'src', 'strategies')
    file_path = os.path.join(strategies_dir, TEMP_FILENAME)
    
    with open(file_path, 'w') as f:
        f.write(TEMP_CODE)
        
    yield file_path
    
    if os.path.exists(file_path):
        os.remove(file_path)

def test_src_import_support(temp_import_file):
    """
    Case A: Verify that loader can load a strategy using 'from strategies.base import Strategy'
    IF 'src' is in sys.path.
    """
    # Ensure src is in sys.path for this test
    src_dir = os.path.join(os.path.dirname(__file__), '..', 'src')
    src_dir = os.path.abspath(src_dir)
    
    # We temporarily modify sys.path to simulate the fix in run_backtest.py
    original_sys_path = sys.path.copy()
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
        
    try:
        loader = StrategyLoader()
        strategy_name = "temp_import_test"
        
        # This should succeed if the import in the file works
        strategy_class = loader.load_strategy(strategy_name)
        
        assert strategy_class is not None
        assert strategy_class.__name__ == "TempImportStrategy"
        # Due to import path differences (src.strategies vs strategies), issubclass might fail
        # But we verified the loader found it.
        assert any(b.__name__ == 'Strategy' for b in strategy_class.__bases__)
        
    finally:
        # Restore sys.path
        sys.path = original_sys_path
