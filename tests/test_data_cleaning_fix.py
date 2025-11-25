import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from src.data_engine import DataManager

@pytest.fixture
def data_engine(tmp_path):
    db_path = str(tmp_path / "test_cleaning.db")
    engine = DataManager(db_path)
    engine.init_db()
    return engine

def test_data_cleaning_volume_nan_survival(data_engine):
    """
    Case A: Volume NaN Survival
    Verify that rows with valid prices but NaN volume are PRESERVED,
    and Volume is filled with 0.
    """
    # Create a DataFrame with some NaN volumes
    dates = pd.date_range(start='2023-01-01', periods=5)
    data = {
        'open': [100.0, 101.0, 102.0, 103.0, 104.0],
        'high': [105.0, 106.0, 107.0, 108.0, 109.0],
        'low': [95.0, 96.0, 97.0, 98.0, 99.0],
        'close': [102.0, 103.0, 104.0, 105.0, 106.0],
        'volume': [1000, np.nan, 2000, np.nan, 3000] # Indices 1 and 3 have NaN volume
    }
    df = pd.DataFrame(data, index=dates)
    df.index.name = 'date'
    
    # We need to manually insert this into the DB to test get_data's cleaning logic
    # OR we can mock the read_sql part. 
    # Let's insert it into the DB to be more integration-like.
    
    conn = data_engine.get_connection()
    cursor = conn.cursor()
    
    # Insert data (including NaNs - sqlite stores them as NULL)
    for date, row in df.iterrows():
        cursor.execute('''
            INSERT INTO ohlcv (ticker, date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('TEST_TICKER', date.strftime('%Y-%m-%d'), row['open'], row['high'], row['low'], row['close'], 
              None if pd.isna(row['volume']) else row['volume']))
    conn.commit()
    conn.close()
    
    # Now fetch it back using get_data
    cleaned_df = data_engine.get_data('TEST_TICKER')
    
    print("\nCleaned DF:\n", cleaned_df)
    
    # Assertions
    # 1. Length should be 5 (no rows dropped)
    assert len(cleaned_df) == 5, f"Expected 5 rows, got {len(cleaned_df)}. Rows with NaN volume were dropped."
    
    # 2. Volume should be 0 where it was NaN
    assert cleaned_df.iloc[1]['volume'] == 0.0
    assert cleaned_df.iloc[3]['volume'] == 0.0
    
    # 3. Prices should be intact
    assert cleaned_df.iloc[1]['close'] == 103.0

def test_data_cleaning_price_nan_drop(data_engine):
    """
    Case B: Price NaN Drop
    Verify that rows with missing essential price data (after ffill) are DROPPED.
    """
    dates = pd.date_range(start='2023-01-01', periods=5)
    data = {
        'open': [100.0, np.nan, 102.0, 103.0, 104.0], # Index 1 has NaN open
        'high': [105.0, 106.0, 107.0, 108.0, 109.0],
        'low': [95.0, 96.0, 97.0, 98.0, 99.0],
        'close': [102.0, 103.0, 104.0, 105.0, 106.0],
        'volume': [1000, 1000, 2000, 3000, 3000]
    }
    df = pd.DataFrame(data, index=dates)
    
    # Note: The current logic we plan to implement uses ffill for prices.
    # So if index 1 is NaN, it might take index 0's value.
    # To test DROP, we need a NaN at the start or a sequence of NaNs that can't be filled?
    # Or if we want to test that it drops if it CANNOT fill.
    # Let's try to put NaN at the very beginning for Open.
    
    data['open'][0] = np.nan
    df = pd.DataFrame(data, index=dates)
    
    conn = data_engine.get_connection()
    cursor = conn.cursor()
    for date, row in df.iterrows():
        cursor.execute('''
            INSERT INTO ohlcv (ticker, date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('TEST_DROP', date.strftime('%Y-%m-%d'), 
              None if pd.isna(row['open']) else row['open'], 
              row['high'], row['low'], row['close'], row['volume']))
    conn.commit()
    conn.close()
    
    cleaned_df = data_engine.get_data('TEST_DROP')
    
    print("\nCleaned DF (Price Drop):\n", cleaned_df)
    
    # If the first row has NaN open, it cannot be ffilled.
    # The second row is also NaN, so it tries to ffill from first (which is NaN), so it stays NaN.
    # So both Index 0 and Index 1 are dropped.
    # Length should be 3.
    assert len(cleaned_df) == 3, f"Expected 3 rows, got {len(cleaned_df)}. Leading NaNs should be dropped."
    assert cleaned_df.index[0] == dates[2] # Should start from third date

