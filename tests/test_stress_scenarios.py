import pytest
import pandas as pd
import numpy as np
from src.backtest_engine import BacktestEngine

@pytest.fixture
def mock_data():
    """Generates mock OHLCV data from 2020-01-01 to 2023-12-31."""
    dates = pd.date_range(start="2020-01-01", end="2023-12-31", freq="D")
    df = pd.DataFrame({
        "open": 100 + np.random.randn(len(dates)).cumsum(),
        "close": 100 + np.random.randn(len(dates)).cumsum(),
        "high": 105 + np.random.randn(len(dates)).cumsum(),
        "low": 95 + np.random.randn(len(dates)).cumsum(),
        "volume": 1000000
    }, index=dates)
    return df

def test_date_slicing_covid_crash(mock_data):
    """
    Case A: Verify that the backtest engine correctly slices data for the COVID-19 crash period.
    """
    engine = BacktestEngine(initial_capital=10000.0)
    
    # Create dummy signals (always hold)
    signals = pd.Series(1.0, index=mock_data.index)
    
    start_date = "2020-01-01"
    end_date = "2020-04-01"
    
    # Run backtest with date slicing
    engine.run(mock_data, signals, start_date=start_date, end_date=end_date)
    
    # Assertions
    assert len(engine.equity_curve) > 0, "Equity curve should not be empty"
    
    # Check that the first and last dates in the equity curve are within the specified range
    # Check that the first and last dates in the equity curve are within the specified range
    first_date = engine.equity_curve.iloc[0]["date"]
    last_date = engine.equity_curve.iloc[-1]["date"]
    
    assert first_date >= pd.Timestamp(start_date), f"First date {first_date} should be >= {start_date}"
    assert last_date <= pd.Timestamp(end_date), f"Last date {last_date} should be <= {end_date}"
    
    # Verify that we didn't process data outside the range
    # The equity curve length should roughly match the number of trading days in that period
    # 2020-01-01 to 2020-04-01 is roughly 90 days, minus weekends ~60-65 days
    assert 50 < len(engine.equity_curve) < 100, f"Unexpected number of days processed: {len(engine.equity_curve)}"

def test_date_slicing_start_only(mock_data):
    """Verify slicing with only start_date."""
    engine = BacktestEngine()
    signals = pd.Series(1.0, index=mock_data.index)
    start_date = "2023-01-01"
    
    engine.run(mock_data, signals, start_date=start_date)
    
    assert len(engine.equity_curve) > 0
    assert engine.equity_curve.iloc[0]["date"] >= pd.Timestamp(start_date)
    # Should go to the end of the data
    assert engine.equity_curve.iloc[-1]["date"] == mock_data.index[-1]

def test_date_slicing_end_only(mock_data):
    """Verify slicing with only end_date."""
    engine = BacktestEngine()
    signals = pd.Series(1.0, index=mock_data.index)
    end_date = "2020-06-01"
    
    engine.run(mock_data, signals, end_date=end_date)
    
    assert len(engine.equity_curve) > 0
    assert engine.equity_curve.iloc[0]["date"] == mock_data.index[0]
    assert engine.equity_curve.iloc[-1]["date"] <= pd.Timestamp(end_date)
