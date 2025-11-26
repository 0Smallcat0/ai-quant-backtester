import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.strategies.loader import StrategyLoadError
from src.strategies.presets import PRESET_STRATEGIES

# We need to test the logic inside run_backtest.py. 
# Since run_backtest.py is a script, it's better to extract the loading logic or mock the parts around it.
# However, the user asked to "Fix src/run_backtest.py", implying we should modify the script.
# To test the script logic without running the whole script, we can import the main function or 
# ideally, refactor the loading logic into a function. 
# But sticking to the plan, we will simulate the CLI execution or mock the environment.

# Better approach for unit testing the logic:
# We can't easily import 'main' and test it because it runs the whole backtest.
# We will create a helper function in the test that replicates the logic we intend to write,
# OR we can refactor run_backtest.py to have a `load_strategy_from_args` function.
# Refactoring is cleaner. Let's assume we will refactor run_backtest.py slightly to make it testable,
# or we test the logic by mocking the arguments and running the block.

# Let's try to verify the logic by creating a test that mocks the argparse and runs the relevant part.
# Actually, the user asked to "Fix run_backtest.py", so let's verify the behavior by running the script via subprocess 
# or by mocking `sys.argv` and `argparse`.

# Wait, the prompt says "TDD - 建立名稱容錯測試".
# Let's write a test that imports the *modified* run_backtest module. 
# But run_backtest.py is a script. 
# Let's assume we will extract the loading logic to a function `get_strategy_class` in run_backtest.py 
# or just test the logic by simulating the script run.

# Let's go with mocking `sys.argv` and patching `BacktestEngine` to avoid running the actual backtest.
# We want to verify that the correct strategy class is loaded.

from src import run_backtest

@pytest.fixture
def mock_loader():
    with patch('src.run_backtest.StrategyLoader') as MockLoader:
        loader_instance = MockLoader.return_value
        yield loader_instance

@pytest.fixture
def mock_engine():
    with patch('src.run_backtest.BacktestEngine') as MockEngine:
        yield MockEngine

@pytest.fixture
def mock_data_manager():
    with patch('src.run_backtest.DataManager') as MockDM:
        dm_instance = MockDM.return_value
        # Return a dummy dataframe
        import pandas as pd
        dm_instance.get_data.return_value = pd.DataFrame({'close': [100, 101, 102]}, index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']))
        yield dm_instance

def test_fuzzy_load_exact_match(mock_loader, mock_engine, mock_data_manager):
    """Case A: Exact Match - RSIStrategy"""
    # Setup
    test_args = ['src/run_backtest.py', '--strategy_name', 'RSIStrategy', '--ticker', 'BTC-USD']
    
    # Mock loader to return None first (simulating it's not a file) OR return the class if it finds it.
    # Actually, the logic is: Try Loader -> If fail, Try Presets.
    # If we pass 'RSIStrategy', Loader might find it if it's in presets? 
    # Loader.load_strategy checks presets first.
    
    # Let's assume Loader works as expected for exact match.
    # We want to test that run_backtest uses it.
    
    with patch.object(sys, 'argv', test_args):
        # We need to prevent the script from actually running the backtest and exiting
        # We can patch 'run_backtest.BacktestEngine.run'
        
        # Configure mock loader to return a MockStrategy class
        MockStrategy = MagicMock()
        mock_strategy_instance = MockStrategy.return_value
        import pandas as pd
        mock_strategy_instance.generate_signals.return_value = pd.DataFrame({'signal': [1, 0, -1]}, index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']))
        mock_loader.load_strategy.return_value = MockStrategy

        # But run_backtest.py executes main() under if __name__ == "__main__".
        # We can import main and run it.
        try:
            run_backtest.main()
        except SystemExit:
            pass
        
        # Verify loader was called
        mock_loader.load_strategy.assert_called_with('RSIStrategy')

def test_fuzzy_load_short_name(mock_loader, mock_engine, mock_data_manager):
    """Case B: Short Name - RSI -> RSIStrategy"""
    test_args = ['src/run_backtest.py', '--strategy_name', 'RSI', '--ticker', 'BTC-USD']
    
    # Mock loader to fail for "RSI"
    mock_loader.load_strategy.side_effect = StrategyLoadError("Not found")
    
    with patch.object(sys, 'argv', test_args):
        # We need to spy on the strategy class instantiation or check if the correct class was picked.
        # Since we can't easily access the local variable `strategy_class` inside main,
        # we can check if BacktestEngine was initialized and run, 
        # AND check if the strategy passed to it (indirectly via signals) is correct?
        # No, engine.run takes signals.
        
        # We can check which class was instantiated.
        # The script does: strategy = strategy_class(**params)
        
        # We can patch the PRESET_STRATEGIES in run_backtest to spy on them.
        with patch('src.run_backtest.PRESET_STRATEGIES') as mock_presets:
            # Setup mock presets
            MockRSI = MagicMock()
            # Configure MockRSI instance to return a valid signals DataFrame
            mock_rsi_instance = MockRSI.return_value
            import pandas as pd
            mock_rsi_instance.generate_signals.return_value = pd.DataFrame({'signal': [1, 0, -1]}, index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']))
            
            mock_presets.__contains__.side_effect = lambda key: key in ["RSIStrategy"]
            mock_presets.__getitem__.side_effect = lambda key: MockRSI if key == "RSIStrategy" else None
            mock_presets.items.return_value = [("RSIStrategy", MockRSI)]
            
            try:
                run_backtest.main()
            except SystemExit:
                pass
            
            # Assert that RSIStrategy was used even though we passed "RSI"
            # The logic should try "RSI" -> Fail -> Try "RSIStrategy" -> Success
            
            # Check if MockRSI was instantiated
            assert MockRSI.called, "RSIStrategy should have been instantiated for input 'RSI'"

def test_fuzzy_load_case_insensitive(mock_loader, mock_engine, mock_data_manager):
    """Case C: Case Insensitive - rsi -> RSIStrategy"""
    test_args = ['src/run_backtest.py', '--strategy_name', 'rsi', '--ticker', 'BTC-USD']
    
    mock_loader.load_strategy.side_effect = StrategyLoadError("Not found")
    
    with patch.object(sys, 'argv', test_args):
        with patch('src.run_backtest.PRESET_STRATEGIES') as mock_presets:
            MockRSI = MagicMock()
            mock_rsi_instance = MockRSI.return_value
            import pandas as pd
            mock_rsi_instance.generate_signals.return_value = pd.DataFrame({'signal': [1, 0, -1]}, index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']))

            # Mock dictionary behavior for iteration
            mock_presets.items.return_value = [("RSIStrategy", MockRSI), ("MovingAverageStrategy", MagicMock())]
            mock_presets.__contains__.return_value = False # "rsi" is not in presets directly
            
            try:
                run_backtest.main()
            except SystemExit:
                pass
            
            assert MockRSI.called, "RSIStrategy should have been instantiated for input 'rsi'"

def test_fuzzy_load_failure(mock_loader, mock_engine, mock_data_manager):
    """Case D: Loader Fail Fallback - Unknown -> ValueError"""
    test_args = ['src/run_backtest.py', '--strategy_name', 'Unknown', '--ticker', 'BTC-USD']
    
    mock_loader.load_strategy.side_effect = StrategyLoadError("Not found")
    
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(ValueError, match="Strategy 'Unknown' not found"):
            run_backtest.main()
