import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from src.data_engine import DataManager

def test_normalization_check():
    """
    Case A: Verify that get_data returns lowercase columns even if DB/processing returns TitleCase.
    """
    # Mock DB connection and read_sql
    with patch('src.data_engine.sqlite3.connect') as mock_connect:
        with patch('pandas.read_sql') as mock_read_sql:
            # Setup mock dataframe with TitleCase columns (simulating the bug or raw data)
            mock_df = pd.DataFrame({
                'date': pd.to_datetime(['2023-01-01', '2023-01-02']),
                'Open': [100.0, 101.0],
                'High': [105.0, 106.0],
                'Low': [95.0, 96.0],
                'Close': [102.0, 103.0],
                'Volume': [1000, 1100]
            })
            mock_read_sql.return_value = mock_df
            
            dm = DataManager("dummy.db")
            df = dm.get_data("BTC-USD")
            
            # Assert all columns are lowercase
            expected_cols = ['open', 'high', 'low', 'close', 'volume']
            assert all(col in df.columns for col in expected_cols)
            assert 'Close' not in df.columns
            assert 'close' in df.columns

def test_strategy_compatibility():
    """
    Case B: Verify that a strategy accessing 'close' works with the returned data.
    """
    # Reuse the logic from Case A to get the dataframe
    with patch('src.data_engine.sqlite3.connect') as mock_connect:
        with patch('pandas.read_sql') as mock_read_sql:
            mock_df = pd.DataFrame({
                'date': pd.to_datetime(['2023-01-01']),
                'Open': [100.0],
                'High': [105.0],
                'Low': [95.0],
                'Close': [102.0],
                'Volume': [1000]
            })
            mock_read_sql.return_value = mock_df
            
            dm = DataManager("dummy.db")
            df = dm.get_data("BTC-USD")
            
            # Simulate strategy access
            try:
                close_prices = df['close']
                assert len(close_prices) == 1
                assert close_prices.iloc[0] == 102.0
            except KeyError as e:
                pytest.fail(f"Strategy failed to access 'close' column: {e}")
