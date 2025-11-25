import pytest
import sys
from unittest.mock import patch, MagicMock
import argparse
from src.run_backtest import main
from src.data_engine import DataManager

import pandas as pd

# Mock DataManager to avoid actual DB calls
@pytest.fixture
def mock_data_manager():
    with patch('src.run_backtest.DataManager') as MockDM:
        instance = MockDM.return_value
        # Setup default return for get_data to be a non-empty DataFrame
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.index = pd.to_datetime(['2023-01-01', '2023-01-02']) # Dummy index
        mock_df.__getitem__.return_value = mock_df # Support chained filtering
        instance.get_data.return_value = mock_df
        yield instance

@pytest.fixture
def mock_strategy_loader():
    with patch('src.run_backtest.StrategyLoader') as MockSL:
        instance = MockSL.return_value
        # Setup load_strategy to return a dummy strategy class
        mock_strategy_class = MagicMock()
        mock_strategy_instance = mock_strategy_class.return_value
        # Setup generate_signals to return a DataFrame with 'signal' column
        signals_df = MagicMock()
        signals_df.columns = ['signal']
        signals_df.__getitem__.return_value = [1, 0] # Dummy signals
        mock_strategy_instance.generate_signals.return_value = signals_df
        
        instance.load_strategy.return_value = mock_strategy_class
        yield instance

@pytest.fixture
def mock_backtest_engine():
    with patch('src.run_backtest.BacktestEngine') as MockBE:
        instance = MockBE.return_value
        instance.trades = []
        instance.equity_curve = [{'date': '2023-01-01', 'equity': 10000}, {'date': '2023-01-02', 'equity': 10100}]
        instance.initial_capital = 10000.0
        yield instance

def test_cli_quotes_strip(mock_data_manager, mock_strategy_loader, mock_backtest_engine):
    """
    Case A: Verify that CLI arguments with extra quotes are stripped.
    """
    test_args = [
        'run_backtest.py',
        '--strategy_name', "'MovingAverage'",
        '--ticker', "'BTC-USD'",
        '--start', "'2023-01-01'",
        '--end', '"2023-12-31"'
    ]
    
    with patch.object(sys, 'argv', test_args):
        # We need to mock print to avoid cluttering stdout and to check for errors if any
        # with patch('builtins.print'):
        main()
            
    # Verify DataManager.get_data was called with sanitized ticker
    mock_data_manager.get_data.assert_called_with('BTC-USD')
    
    # Verify StrategyLoader.load_strategy was called with sanitized strategy name
    mock_strategy_loader.load_strategy.assert_called_with('MovingAverage')

def test_data_engine_sanitization():
    """
    Case B: Verify that DataEngine.get_data sanitizes input ticker.
    """
    # We need a real or partially real DataManager for this, or just test the method logic if we can isolate it.
    # Since DataManager connects to DB, let's mock the DB connection but test the input processing logic.
    # Actually, looking at the code, get_data calls get_connection.
    # We can just instantiate DataManager with a dummy path and mock get_connection.
    
    dm = DataManager(db_path=':memory:')
    
    with patch.object(dm, 'get_connection') as mock_conn:
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor
        
        # Mock pd.read_sql to return empty so we don't crash on processing, 
        # or better, just check the call arguments before it proceeds to read_sql.
        # However, read_sql takes the connection.
        
        with patch('pandas.read_sql') as mock_read_sql:
            mock_read_sql.return_value = MagicMock(empty=True) # Return empty to trigger the empty check or just return
            
            # We expect it to raise ValueError because we return empty df, 
            # but we want to check the call args to read_sql or the query params.
            try:
                dm.get_data("'AAPL'")
            except ValueError:
                pass # Expected because of empty df
            
            # Check if the ticker passed to read_sql params was sanitized
            # The code uses params=(ticker,)
            call_args = mock_read_sql.call_args
            # call_args[0] is args, call_args[1] is kwargs
            # args: (query, conn)
            # kwargs: params=(ticker,)
            
            # Wait, read_sql signature is (sql, con, index_col=None, coerce_float=True, params=None, ...)
            # The code calls: pd.read_sql(query, conn, params=(ticker,))
            
            # Let's verify the params passed to read_sql
            _, kwargs = mock_read_sql.call_args
            assert kwargs['params'][0] == 'AAPL', "Ticker should be sanitized to 'AAPL'"

def test_normalize_ticker_sanitization():
    """
    Test normalize_ticker explicitly for quote stripping.
    """
    dm = DataManager(db_path=':memory:')
    
    assert dm.normalize_ticker("'BTC'") == 'BTC-USD'
    assert dm.normalize_ticker('"ETH"') == 'ETH-USD'
    assert dm.normalize_ticker("'AAPL'") == 'AAPL'
