import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.strategies.loader import StrategyLoadError
from src.strategies.presets import PRESET_STRATEGIES
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
    """Case A: Exact Match - SentimentRSIStrategy"""
    test_args = ['src/run_backtest.py', '--strategy_name', 'SentimentRSIStrategy', '--ticker', 'BTC-USD']
    
    with patch.object(sys, 'argv', test_args):
        MockStrategy = MagicMock()
        mock_strategy_instance = MockStrategy.return_value
        import pandas as pd
        mock_strategy_instance.generate_signals.return_value = pd.DataFrame({'signal': [1, 0, -1]}, index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']))
        mock_loader.load_strategy.return_value = MockStrategy

        try:
            run_backtest.main()
        except SystemExit:
            pass
        
        mock_loader.load_strategy.assert_called_with('SentimentRSIStrategy')

def test_fuzzy_load_short_name(mock_loader, mock_engine, mock_data_manager):
    """Case B: Short Name - SentimentRSI -> SentimentRSIStrategy"""
    test_args = ['src/run_backtest.py', '--strategy_name', 'SentimentRSI', '--ticker', 'BTC-USD']
    
    mock_loader.load_strategy.side_effect = StrategyLoadError("Not found")
    
    with patch.object(sys, 'argv', test_args):
        with patch('src.run_backtest.PRESET_STRATEGIES') as mock_presets:
            MockRSI = MagicMock()
            mock_rsi_instance = MockRSI.return_value
            import pandas as pd
            mock_rsi_instance.generate_signals.return_value = pd.DataFrame({'signal': [1, 0, -1]}, index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']))
            
            # Simulate behavior: "SentimentRSIStrategy" is in presets
            mock_presets.__contains__.side_effect = lambda key: key == "SentimentRSIStrategy"
            mock_presets.__getitem__.side_effect = lambda key: MockRSI if key == "SentimentRSIStrategy" else None
            mock_presets.items.return_value = [("SentimentRSIStrategy", MockRSI)]
            
            try:
                run_backtest.main()
            except SystemExit:
                pass
            
            assert MockRSI.called, "SentimentRSIStrategy should have been instantiated for input 'SentimentRSI'"

def test_fuzzy_load_case_insensitive(mock_loader, mock_engine, mock_data_manager):
    """Case C: Case Insensitive - sentimentrsi -> SentimentRSIStrategy"""
    test_args = ['src/run_backtest.py', '--strategy_name', 'sentimentrsi', '--ticker', 'BTC-USD']
    
    mock_loader.load_strategy.side_effect = StrategyLoadError("Not found")
    
    with patch.object(sys, 'argv', test_args):
        with patch('src.run_backtest.PRESET_STRATEGIES') as mock_presets:
            MockRSI = MagicMock()
            mock_rsi_instance = MockRSI.return_value
            import pandas as pd
            mock_rsi_instance.generate_signals.return_value = pd.DataFrame({'signal': [1, 0, -1]}, index=pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']))

            mock_presets.items.return_value = [("SentimentRSIStrategy", MockRSI), ("MovingAverageStrategy", MagicMock())]
            mock_presets.__contains__.return_value = False
            
            try:
                run_backtest.main()
            except SystemExit:
                pass
            
            assert MockRSI.called, "SentimentRSIStrategy should have been instantiated for input 'sentimentrsi'"

def test_fuzzy_load_failure(mock_loader, mock_engine, mock_data_manager):
    """Case D: Loader Fail Fallback - Unknown -> ValueError"""
    test_args = ['src/run_backtest.py', '--strategy_name', 'Unknown', '--ticker', 'BTC-USD']
    
    mock_loader.load_strategy.side_effect = StrategyLoadError("Not found")
    
    with patch.object(sys, 'argv', test_args):
        # run_backtest.main() catches ValueError and prints it, then exits with 1.
        # So we expect SystemExit(1)
        with pytest.raises(SystemExit) as cm:
            run_backtest.main()
        assert cm.value.code == 1
