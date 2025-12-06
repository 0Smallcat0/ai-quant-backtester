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
        try:
            os.remove(db_path)
        except:
            pass
    
    manager = DataManager(db_path)
    manager.init_db()
    
    yield manager
    
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except:
            pass

def test_duplicate_removal(temp_db):
    """
    Case A: Simulate fetch_data returning overlapping dates.
    Assert that the final data in DB/DataFrame has no duplicates.
    """
    ticker = "TEST_DUP"
    dates1 = pd.date_range(start="2023-01-01", end="2023-01-02")
    data1 = pd.DataFrame({
        'Open': [100, 101], 'High': [105, 106], 'Low': [95, 96], 'Close': [102, 103], 'Volume': [1000, 1100]
    }, index=dates1)
    
    dates2 = pd.date_range(start="2023-01-02", end="2023-01-03")
    data2 = pd.DataFrame({
        'Open': [101, 102], 'High': [106, 107], 'Low': [96, 97], 'Close': [103, 104], 'Volume': [1100, 1200]
    }, index=dates2)
    
    # We simulate separate calls to fetch_data by making yf.download return one then the other
    # But simpler: Just patch twice.
    with patch('yfinance.download', return_value=data1):
        temp_db.fetch_data(ticker, start_date="2023-01-01", end_date="2023-01-02")
            
    with patch('yfinance.download', return_value=data2):
        temp_db.fetch_data(ticker, start_date="2023-01-02", end_date="2023-01-03")
            
    df = temp_db.get_data(ticker)
    assert len(df) == 3, f"Expected 3 rows, got {len(df)}"
    assert df.index.is_unique, "Index should be unique"

def test_empty_data_guard(temp_db):
    """
    Case B: Simulate get_data returning empty DataFrame (or cleaned to empty).
    Assert ValueError is raised.
    """
    ticker = "EMPTY_TICKER"
    with pytest.raises(ValueError, match="No valid data for ticker"):
        temp_db.get_data(ticker)

def test_ticker_normalization_fail(temp_db):
    """
    Case C: Simulate normalize_ticker failure.
    Assert it returns default {ticker}.TW
    """
    ticker = "9999"
    with patch('yfinance.Ticker') as mock_ticker:
        mock_ticker.side_effect = Exception("API Error")
        normalized = temp_db.normalize_ticker(ticker)
        assert normalized == "9999.TW"

def test_smart_imputation_and_filtering(temp_db):
    """
    Case D: Verify Smart Imputation (Zero Volume) and Future/Tail Filtering.
    """
    ticker = "TEST_SMART"
    
    real_today = pd.Timestamp.now().normalize()
    future_date = real_today + pd.Timedelta(days=5)
    
    dates = [
        real_today - pd.Timedelta(days=4), # Day -4
        real_today - pd.Timedelta(days=3), # Day -3 (Zero Vol)
        real_today - pd.Timedelta(days=2), # Day -2
        real_today - pd.Timedelta(days=0), # Today (Zero Vol - Last one considered present) 
        future_date                        # Future
    ]
    
    data = pd.DataFrame({
        'Open': [100.0] * 5,
        'High': [100.0] * 5,
        'Low': [100.0] * 5,
        'Close': [100.0] * 5,
        'Volume': [1000.0, 0.0, 1000.0, 0.0, 500.0] # 500 future, 0.0 today
    }, index=dates)
    
    with patch('yfinance.download', return_value=data):
        temp_db.fetch_data(ticker, start_date="2024-01-01")
        
    df = temp_db.get_data(ticker)
    
    # 1. Future Filter
    assert future_date not in df.index, "Future date should be filtered out"
    
    # 2. Tail Check
    today_ts = dates[3]
    assert today_ts not in df.index, "Last row with zero volume should be dropped"
    
    # 3. Smart Imputation
    day_3_ts = dates[1]
    assert day_3_ts in df.index, "Middle zero volume row should be kept"
    
    vol_day_3 = df.loc[day_3_ts, 'volume']
    assert vol_day_3 > 0, f"Middle zero volume should be imputed. Got {vol_day_3}"
    assert vol_day_3 == 1000.0, f"Should impute from previous day (1000). Got {vol_day_3}"
