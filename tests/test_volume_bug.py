import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from src.data_engine import DataManager
import os

# Mock data for 0056.TW with NaN volumes or weird structure
def mock_0056_data(*args, **kwargs):
    dates = pd.date_range(start='2023-01-01', periods=5)
    data = {
        'Open': [30.0, 30.5, 31.0, 30.8, 31.2],
        'High': [30.5, 31.0, 31.5, 31.0, 31.5],
        'Low': [29.8, 30.2, 30.8, 30.5, 31.0],
        'Close': [30.2, 30.8, 31.2, 30.9, 31.4],
        'Volume': [1000, np.nan, 2000, np.nan, 3000] # Mixed NaN
    }
    df = pd.DataFrame(data, index=dates)
    return df

def mock_0056_zero_volume(*args, **kwargs):
    dates = pd.date_range(start='2023-01-01', periods=5)
    data = {
        'Open': [30.0, 30.5, 31.0, 30.8, 31.2],
        'High': [30.5, 31.0, 31.5, 31.0, 31.5],
        'Low': [29.8, 30.2, 30.8, 30.5, 31.0],
        'Close': [30.2, 30.8, 31.2, 30.9, 31.4],
        'Volume': [0, 0, 0, 0, 0] # All Zeros (Simulating bad auto_adjust)
    }
    df = pd.DataFrame(data, index=dates)
    return df

@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_data.db")

@pytest.fixture
def data_engine(db_path):
    engine = DataManager(db_path)
    engine.init_db()
    return engine

def test_fetch_data_nan_handling(data_engine):
    """
    Case B: NaN Handling
    Verify that NaNs in Volume are handled (filled) and don't result in data loss or zeroing of valid data.
    """
    with patch('yfinance.download', side_effect=mock_0056_data):
        data_engine.fetch_data("0056.TW")
        
        df = data_engine.get_data("0056.TW")
        
        # Check if we have data
        assert not df.empty
        
        # Check Volume
        # We expect NaNs to be filled, ideally with ffill.
        # If the current logic just drops NaNs, we might lose rows.
        # If it keeps NaNs, they might be 0 or NaN.
        
        print("\nFetched Data:\n", df)
        
        # In the original code, it does dropna(), so we might lose rows 2 and 4 (index 1 and 3)
        # The user wants us to fix this so we DON'T lose rows, but fill volume.
        
        # Assert that we have all 5 rows (meaning we didn't drop them)
        # This assertion is expected to FAIL before the fix if the current code drops rows with NaN volume
        assert len(df) == 5, f"Expected 5 rows, got {len(df)}. Rows with NaN volume might have been dropped."
        
        # Assert Volume is not NaN and not all zero
        assert df['volume'].notna().all()
        assert (df['volume'] > 0).any()

def test_fetch_data_column_normalization(data_engine):
    """
    Case A/B: Column Normalization
    Verify that 'Volume' (capitalized) is correctly normalized to 'volume'.
    """
    with patch('yfinance.download', side_effect=mock_0056_data):
        data_engine.fetch_data("0056.TW")
        df = data_engine.get_data("0056.TW")
        assert 'volume' in df.columns
        assert 'Volume' not in df.columns

