import unittest
from unittest.mock import patch
import sys
from src.run_backtest import main

class TestCLIDateAlias(unittest.TestCase):
    
    @patch('src.run_backtest.DataManager')
    @patch('src.run_backtest.StrategyLoader')
    @patch('src.run_backtest.BacktestEngine')
    def test_standard_date_args(self, mock_engine, mock_loader, mock_data_manager):
        """
        Case A: Verify --start and --end work (Standard).
        """
        with patch.object(sys, 'argv', ["src/run_backtest.py", "--strategy_name", "TestStrategy", "--start", "2023-01-01", "--end", "2023-12-31"]):
             mock_dm_instance = mock_data_manager.return_value
             import pandas as pd
             from unittest.mock import MagicMock
             df = pd.DataFrame({'close': [100]}, index=pd.to_datetime(['2023-06-01']))
             mock_dm_instance.get_data.return_value = df
             
             # Mock Strategy Class and Instance
             mock_strategy_instance = MagicMock()
             mock_strategy_instance.generate_signals.return_value = pd.DataFrame({'signal': [1]}, index=df.index)
             mock_strategy_class = MagicMock(return_value=mock_strategy_instance)
             mock_loader.return_value.load_strategy.return_value = mock_strategy_class
             
             mock_engine.return_value.equity_curve = []
             mock_engine.return_value.trades = []
             
             try:
                 main()
             except SystemExit:
                 pass
             
             mock_dm_instance.get_data.assert_called()

    @patch('src.run_backtest.DataManager')
    @patch('src.run_backtest.StrategyLoader')
    @patch('src.run_backtest.BacktestEngine')
    def test_alias_date_args(self, mock_engine, mock_loader, mock_data_manager):
        """
        Case B: Verify --start_date and --end_date work (Alias).
        """
        with patch.object(sys, 'argv', ["src/run_backtest.py", "--strategy_name", "TestStrategy", "--start_date", "2023-01-01", "--end_date", "2023-12-31"]):
             mock_dm_instance = mock_data_manager.return_value
             import pandas as pd
             from unittest.mock import MagicMock
             df = pd.DataFrame({'close': [100]}, index=pd.to_datetime(['2023-06-01']))
             mock_dm_instance.get_data.return_value = df
             
             # Mock Strategy Class and Instance
             mock_strategy_instance = MagicMock()
             mock_strategy_instance.generate_signals.return_value = pd.DataFrame({'signal': [1]}, index=df.index)
             mock_strategy_class = MagicMock(return_value=mock_strategy_instance)
             mock_loader.return_value.load_strategy.return_value = mock_strategy_class
             
             mock_engine.return_value.equity_curve = []
             mock_engine.return_value.trades = []
             
             try:
                 main()
             except SystemExit:
                 pass
             
             mock_engine.return_value.run.assert_called()

if __name__ == '__main__':
    unittest.main()
