import pytest
import pandas as pd
import numpy as np

def crop_sentiment_dataframe(df: pd.DataFrame, buffer_days: int = 5, threshold: float = 0.001) -> pd.DataFrame:
    """
    Simulation of the logic to be implemented in src/ui/data_management.py
    """
    if 'sentiment' not in df.columns:
        return df
    
    # Check for valid sentiment data (absolute value > threshold)
    valid_sentiment = df[df['sentiment'].abs() > threshold]
    
    if valid_sentiment.empty:
        # If no valid sentiment, return empty or handle as "no data"
        # Ideally, we might want to return nothing to indicate "No Valid Data"
        return pd.DataFrame(columns=df.columns)
    
    first_valid_idx = valid_sentiment.index.min()
    
    # Calculate start date with buffer
    start_date = first_valid_idx - pd.Timedelta(days=buffer_days)
    
    # ensure we don't go before the actual start of the dataframe? 
    # Actually, slicing with a date before the index start is fine in pandas, it just takes from beginning.
    # But we want to CROP. So we slice [start_date:]
    
    return df[start_date:]

def test_crop_sentiment_long_history_of_zeros():
    # Create dates from 2010 to 2025
    dates = pd.date_range(start="2010-01-01", end="2025-12-31", freq='D')
    df = pd.DataFrame(index=dates)
    df['sentiment'] = 0.0
    
    # Add valid data in last 10 days
    valid_start_date = pd.Timestamp("2025-12-20")
    df.loc[valid_start_date:, 'sentiment'] = 0.5
    
    cropped = crop_sentiment_dataframe(df)
    
    # Expect start date to be around 2025-12-15 (5 days buffer)
    expected_start_approx = valid_start_date - pd.Timedelta(days=5)
    
    assert cropped.index.min() >= expected_start_approx
    assert cropped.index.min() < valid_start_date
    assert len(cropped) < 30 # Should be very short, definitely not thousands of rows
    assert len(cropped) > 10

def test_crop_sentiment_all_zeros():
    dates = pd.date_range(start="2025-01-01", end="2025-01-31", freq='D')
    df = pd.DataFrame(index=dates)
    df['sentiment'] = 0.0
    
    cropped = crop_sentiment_dataframe(df)
    
    # Should be empty
    assert cropped.empty

def test_crop_sentiment_valid_from_start():
    dates = pd.date_range(start="2025-01-01", end="2025-01-31", freq='D')
    df = pd.DataFrame(index=dates)
    df['sentiment'] = 0.5
    
    cropped = crop_sentiment_dataframe(df)
    
    # Should be full length (or close to it/same start)
    assert len(cropped) == len(df)
    assert cropped.index.min() == df.index.min()

def test_crop_sentiment_noise_handling():
    dates = pd.date_range(start="2025-01-01", end="2025-01-31", freq='D')
    df = pd.DataFrame(index=dates)
    df['sentiment'] = 0.0
    
    # Add noise (below threshold 0.001)
    df.iloc[10, df.columns.get_loc('sentiment')] = 0.0001
    df.iloc[20, df.columns.get_loc('sentiment')] = -0.0009
    
    # Valid data at end
    valid_start = pd.Timestamp("2025-01-30")
    df.loc[valid_start, 'sentiment'] = 0.1
    
    cropped = crop_sentiment_dataframe(df)
    
    # Should skip the noise at index 10 and 20
    # Start buffer ~5 days before Jan 30 -> Jan 25
    expected_start = valid_start - pd.Timedelta(days=5)
    assert cropped.index.min() >= expected_start
