import unittest
from unittest.mock import patch, MagicMock
import sys
import pandas as pd
from src.run_backtest import main

class TestCLIAlias(unittest.TestCase):
    
    @patch('src.run_backtest.DataManager')
    @patch('src.run_backtest.StrategyLoader')
    @patch('src.run_backtest.BacktestEngine')
    @patch('sys.argv')
    def test_ticker_argument(self, mock_argv, mock_engine, mock_loader, mock_data_manager):
        """
        Case A: Verify --ticker argument works.
        """
        # Mock sys.argv
        # We need to mock the whole argv list including script name
        mock_argv.__getitem__.side_effect = lambda x: ["src/run_backtest.py", "--strategy_name", "TestStrategy", "--ticker", "AAPL"][x]
        # Actually, mocking sys.argv directly is better done via patch.object or just passing args to main if main accepted args.
        # But main() parses sys.argv directly.
        
        # Let's use a simpler approach: mock argparse.ArgumentParser.parse_args
        # But we want to test the actual parsing logic.
        
        with patch.object(sys, 'argv', ["src/run_backtest.py", "--strategy_name", "TestStrategy", "--ticker", "AAPL"]):
             # We need to mock the rest of the execution to avoid actual DB/Strategy loading
             # The mocks above (mock_data_manager, etc.) should handle it if instantiated.
             
             # Mock DataManager instance
             mock_dm_instance = mock_data_manager.return_value
             mock_dm_instance.get_data.return_value.empty = False # Data found
             
             # Mock StrategyLoader
             mock_loader_instance = mock_loader.return_value
             mock_strategy_instance = MagicMock()
             # Ensure generate_signals returns a DataFrame with 'signal' column
             mock_strategy_instance.generate_signals.return_value = pd.DataFrame({'signal': [0]*100}) 
             mock_loader_instance.load_strategy.return_value = MagicMock(return_value=mock_strategy_instance)
             
             # Mock BacktestEngine
             mock_engine_instance = mock_engine.return_value
             mock_engine_instance.equity_curve = []
             mock_engine_instance.trades = []
             mock_engine_instance.initial_capital = 10000.0
             mock_engine_instance.initial_capital = 10000.0
             
             try:
                 main()
             except SystemExit:
                 # It might exit if something fails, but we expect success
                 pass
             
             # Verify get_data was called with AAPL
             mock_dm_instance.get_data.assert_called_with("AAPL")

    @patch('src.run_backtest.DataManager')
    @patch('src.run_backtest.StrategyLoader')
    @patch('src.run_backtest.BacktestEngine')
    def test_symbol_alias(self, mock_engine, mock_loader, mock_data_manager):
        """
        Case B: Verify --symbol argument works as alias for --ticker.
        """
        with patch.object(sys, 'argv', ["src/run_backtest.py", "--strategy_name", "TestStrategy", "--symbol", "GOOG"]):
             # Mock DataManager instance
             mock_dm_instance = mock_data_manager.return_value
             mock_dm_instance.get_data.return_value.empty = False
             
             # Mock StrategyLoader
             mock_loader_instance = mock_loader.return_value
             mock_strategy_instance = MagicMock()
             mock_strategy_instance.generate_signals.return_value = pd.DataFrame({'signal': [0]*100})
             mock_loader_instance.load_strategy.return_value = MagicMock(return_value=mock_strategy_instance)
             
             # Mock BacktestEngine
             mock_engine_instance = mock_engine.return_value
             mock_engine_instance.equity_curve = []
             mock_engine_instance.trades = []
             mock_engine_instance.initial_capital = 10000.0
             
             try:
                 main()
             except SystemExit:
                 pass
             
             # Verify get_data was called with GOOG (mapped from --symbol)
             mock_dm_instance.get_data.assert_called_with("GOOG")

if __name__ == '__main__':
    unittest.main()
