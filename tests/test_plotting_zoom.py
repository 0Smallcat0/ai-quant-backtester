import pytest
import pandas as pd
import plotly.graph_objects as go
from src.ui.plotting import plot_price_history

def test_smart_zoom_with_sparse_sentiment():
    """
    Scenario: Data from 2020-2023. Sentiment only exists in last 5 days.
    Current Behavior (Default): Zooms to last 30 days.
    Target Behavior (Smart): Zooms to last 7 days (5 days data + 2 days padding).
    """
    # 1. Setup Mock Data (3 years of data)
    dates = pd.date_range(start='2020-01-01', end='2023-01-01', freq='D')
    df = pd.DataFrame(index=dates)
    df['open'] = 100
    df['high'] = 110
    df['low'] = 90
    df['close'] = 105
    df['sentiment'] = 0.0 # Initialize all 0

    # 2. Add Valid Sentiment at the very end (last 5 days)
    # 2022-12-28 to 2023-01-01
    df.loc['2022-12-28':, 'sentiment'] = 0.5 

    # 3. Generate Plot
    fig = plot_price_history(df, "TEST-TICKER")

    # 4. Extract Range
    # Plotly stores range in layout.xaxis.range
    # It might be None if autorange is true, but plot_price_history sets it explicitly.
    x_range = fig.layout.xaxis.range
    assert x_range is not None, "X-Axis range should be explicitly set"
    
    start_date_str = x_range[0]
    # Handle both string and datetime (Plotly often uses strings for dates)
    start_date = pd.to_datetime(start_date_str)
    
    # 5. Assertions
    # First valid sentiment: 2022-12-28
    # Expected Start: 2022-12-28 - 2 days = 2022-12-26
    expected_start = pd.Timestamp('2022-12-26')
    
    # We allow a small margin of error (e.g. implementation details might vary slightly)
    # But currently the default is T-30 days = 2022-12-02.
    # So 2022-12-26 is significantly different from 2022-12-02.
    
    print(f"Computed Start Date: {start_date}")
    print(f"Expected Start Date: {expected_start}")

    # Check if we are closer to the Smart Zoom target than the Default target
    # If logic is implemented, start_date should be >= 2022-12-26
    # If not implemented, it will be around 2022-12-02
    
    assert start_date >= expected_start, f"Chart zoomed out too far! Got {start_date}, expected >= {expected_start}"
    assert start_date <= pd.Timestamp('2022-12-28'), "Chart zoomed in way too much!"

def test_smart_zoom_all_zero_sentiment():
    """
    Scenario: Sentiment exists but is all 0.
    Expectation: Default 30-day zoom.
    """
    dates = pd.date_range(start='2023-01-01', end='2023-06-01', freq='D')
    df = pd.DataFrame(index=dates)
    df['open'] = 100
    df['high'] = 110
    df['low'] = 90
    df['close'] = 105
    df['sentiment'] = 0.0

    fig = plot_price_history(df, "TEST-ZERO")
    x_range = fig.layout.xaxis.range
    
    start_date = pd.to_datetime(x_range[0])
    last_date = df.index.max()
    expected_default_start = last_date - pd.Timedelta(days=30)
    
    assert start_date == expected_default_start, "Should default to 30 days if sentiment is all zero"

def test_no_sentiment_column():
    """
    Scenario: formatting compatibility check.
    """
    dates = pd.date_range(start='2023-01-01', end='2023-02-01', freq='D')
    df = pd.DataFrame(index=dates)
    df['open'] = 100
    df['high'] = 110
    df['low'] = 90
    df['close'] = 105
    # No sentiment column

    fig = plot_price_history(df, "TEST-NO-COL")
    x_range = fig.layout.xaxis.range
    assert x_range is not None
