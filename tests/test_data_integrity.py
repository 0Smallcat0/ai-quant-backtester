import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from src.data_engine import DataManager
import sqlite3
import os

# Fixture for temporary database
@pytest.fixture
def temp_db():
    db_path = "test_data_integrity.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    manager = DataManager(db_path)
    manager.init_db()
    
    yield manager
    
    if os.path.exists(db_path):
        os.remove(db_path)

def test_duplicate_removal(temp_db):
    """
    Case A: Simulate fetch_data returning overlapping dates.
    Assert that the final data in DB/DataFrame has no duplicates.
    """
    ticker = "TEST_DUP"
    
    # Create two chunks with overlapping date '2023-01-02'
    dates1 = pd.date_range(start="2023-01-01", end="2023-01-02")
    data1 = pd.DataFrame({
        'Open': [100, 101], 'High': [105, 106], 'Low': [95, 96], 'Close': [102, 103], 'Volume': [1000, 1100]
    }, index=dates1)
    
    dates2 = pd.date_range(start="2023-01-02", end="2023-01-03")
    data2 = pd.DataFrame({
        'Open': [101, 102], 'High': [106, 107], 'Low': [96, 97], 'Close': [103, 104], 'Volume': [1100, 1200]
    }, index=dates2)
    
    # Mock yf.download to return these chunks
    with patch('yfinance.download', side_effect=[data1, data2]):
        # We need to force fetch_data to loop twice or just mock it such that it processes these.
        # Since fetch_data loops by year, we can simulate this by mocking the loop or just calling internal logic if it was exposed.
        # But fetch_data logic is: loop years -> download -> append to list -> concat.
        # If we just mock yfinance.download to return a list of DFs when called? 
        # No, yf.download is called per year.
        # Let's just mock yf.download to return data1 then data2.
        # And we call fetch_data for a range that covers these.
        
        # However, fetch_data loops by year. 2023-01-01 to 2023-01-03 is all in 2023.
        # So it will only call download ONCE for 2023.
        # To simulate duplicates from *separate* calls (e.g. overlapping years or multiple fetch calls), 
        # we can call fetch_data twice with overlapping ranges?
        # Or better: The user requirement says "Chunk download causing duplicate dates".
        # This usually happens if we fetch 2022-2023 and then 2023-2024.
        # But fetch_data iterates by year.
        # Let's simulate calling fetch_data twice.
        
        # Call 1: 2023-01-01 to 2023-01-02
        with patch('yfinance.download', return_value=data1):
            temp_db.fetch_data(ticker, start_date="2023-01-01", end_date="2023-01-02")
            
        # Call 2: 2023-01-02 to 2023-01-03 (Overlapping 01-02)
        with patch('yfinance.download', return_value=data2):
            temp_db.fetch_data(ticker, start_date="2023-01-02", end_date="2023-01-03")
            
    # Now check DB content
    df = temp_db.get_data(ticker)
    
    # Should have 3 rows: 01, 02, 03. Not 4 rows (01, 02, 02, 03).
    assert len(df) == 3, f"Expected 3 rows, got {len(df)}"
    assert df.index.is_unique, "Index should be unique"
    # Check specific date
    # Check specific date
    # If index is unique, loc returns a Series for a single date.
    # If not unique, it returns a DataFrame.
    # We already asserted is_unique, so it should be a Series.
    assert isinstance(df.loc['2023-01-02'], pd.Series), "Should be a Series (single row)"

def test_empty_data_guard(temp_db):
    """
    Case B: Simulate get_data returning empty DataFrame (or cleaned to empty).
    Assert ValueError is raised.
    """
    ticker = "EMPTY_TICKER"
    
    # Ensure DB has no data for this ticker
    # Calling get_data should raise ValueError instead of returning empty DF
    
    with pytest.raises(ValueError, match="No valid data for ticker"):
        temp_db.get_data(ticker)

def test_ticker_normalization_fail(temp_db):
    """
    Case C: Simulate normalize_ticker failure.
    Assert it returns default {ticker}.TW
    """
    ticker = "9999"
    
    # Mock yf.Ticker to raise Exception
    with patch('yfinance.Ticker') as mock_ticker:
        mock_ticker.side_effect = Exception("API Error")
        
        normalized = temp_db.normalize_ticker(ticker)
        
        assert normalized == "9999.TW"
