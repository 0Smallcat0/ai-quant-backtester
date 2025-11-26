import pytest
import pandas as pd
import numpy as np
from src.backtest_engine import BacktestEngine

# Mock Data Fixture
@pytest.fixture
def mock_price_data():
    """
    Creates a simple 5-day OHLCV DataFrame for testing.
    Dates: 2023-01-01 to 2023-01-05
    """
    dates = pd.date_range(start="2023-01-01", periods=5, freq="D")
    data = pd.DataFrame({
        "Open": [100.0, 102.0, 101.0, 103.0, 105.0],
        "High": [105.0, 106.0, 104.0, 108.0, 110.0],
        "Low": [99.0, 101.0, 100.0, 102.0, 104.0],
        "Close": [101.0, 103.0, 102.0, 106.0, 108.0],
        "Volume": [1000, 1200, 1100, 1300, 1400]
    }, index=dates)
    return data

def test_execution_t_plus_1(mock_price_data):
    """
    Test Case 1: T+1 Execution
    Scenario: Day 1 Close signal -> Buy.
    Expected: Trade executed at Day 2 Open.
    """
    engine = BacktestEngine(initial_capital=100000, slippage=0.0)
    
    # Create signals: Buy on Day 1 (index 0)
    signals = pd.Series(0, index=mock_price_data.index)
    signals.iloc[0] = 1  # Buy signal
    signals = signals.replace(0, np.nan).ffill().fillna(0) # Maintain signal
    
    engine.run(mock_price_data, signals)
    
    trades = engine.trades
    assert len(trades) >= 1, "Should have executed at least 1 trade"
    assert engine.position > 0, "Should be long"
    
    # Check execution time and price
    # Day 1 is index 0, Day 2 is index 1
    expected_date = mock_price_data.index[1]
    expected_price = mock_price_data.iloc[1]["Open"]
    
    assert trades[0].entry_date == expected_date, f"Trade should be on {expected_date}"
    assert trades[0].entry_price == expected_price, f"Trade price should be {expected_price}"

def test_position_sizing_fixed_pct(mock_price_data):
    """
    Test Case 2: Position Sizing (Fixed Percent)
    Scenario: Initial 100,000, target 50%.
    Expected: Order value approx 50,000.
    """
    engine = BacktestEngine(initial_capital=100000, slippage=0.0)
    engine.set_position_sizing(method="fixed_percent", target=0.5)
    
    signals = pd.Series(0, index=mock_price_data.index)
    signals.iloc[0] = 1  # Buy signal
    signals = signals.replace(0, np.nan).ffill().fillna(0) # Maintain signal
    
    engine.run(mock_price_data, signals)
    
    trades = engine.trades
    assert len(trades) >= 1
    
    # Check total position value instead of single trade
    current_value = engine.position * mock_price_data.iloc[-1]["Close"]
    expected_value = 50000 # Approx
    
    # Allow for price movement drift (Target-Delta keeps it close to 50% of equity)
    # Equity ~ 100k. Target 50k.
    assert abs(current_value - expected_value) < 5000, f"Position value {current_value} should be close to {expected_value}"

def test_long_only_mode(mock_price_data):
    """
    Test Case 3: Long Only Mode
    Scenario: long_only=True, Short signal.
    Expected: Signal ignored, no trade.
    """
    engine = BacktestEngine(initial_capital=100000, long_only=True, slippage=0.0)
    
    signals = pd.Series(0, index=mock_price_data.index)
    signals.iloc[0] = -1  # Short signal
    signals = signals.replace(0, np.nan).ffill().fillna(0) # Maintain signal
    
    engine.run(mock_price_data, signals)
    
    trades = engine.trades
    assert len(trades) == 0, "Should ignore short signal in long-only mode"

def test_commission_deduction():
    """
    Test Case 4: Commission Deduction
    Scenario: Buy 100 shares at $100 (Value $10,000), Comm 0.1%.
    Expected: Cash deducted = $10,000 + $10 = $10,010.
    """
    # Setup specific data to control price
    dates = pd.date_range(start="2023-01-01", periods=2, freq="D")
    data = pd.DataFrame({
        "Open": [100.0, 100.0], # Buy at 100
        "High": [105.0, 105.0],
        "Low": [95.0, 95.0],
        "Close": [100.0, 100.0],
        "Volume": [1000, 1000]
    }, index=dates)
    
    initial_capital = 100000
    commission_rate = 0.001
    
    engine = BacktestEngine(initial_capital=initial_capital, commission_rate=commission_rate, slippage=0.0)
    
    # We need to force a purchase of 100 shares.
    # If we use fixed_amount = 10000, and price is 100, we get 100 shares.
    engine.set_position_sizing(method="fixed_amount", amount=10000)
    
    signals = pd.Series([1, 1], index=dates) # Buy on Day 1, Hold Day 2
    
    engine.run(data, signals)
    
    trades = engine.trades
    assert len(trades) == 1
    assert trades[0].quantity == pytest.approx(100)
    assert trades[0].entry_price == 100.0
    
    # Calculate expected cash
    # Cost = 100 * 100 = 10000
    # Comm = 10000 * 0.001 = 10
    # Total Ded = 10010
    expected_cash = initial_capital - 10010
    
    assert engine.current_capital == pytest.approx(expected_cash), f"Cash should be {expected_cash}, got {engine.current_capital}"

def test_bankruptcy_protection(mock_price_data):
    """
    Test Case 5: Bankruptcy Protection
    Scenario: Initial 1000, Price 100. Target 100% (or more).
    Expected: Should only buy what we can afford (approx 10 shares).
    """
    engine = BacktestEngine(initial_capital=1000, slippage=0.0, min_commission=0.0)
    # Try to buy way more than we can afford
    engine.set_position_sizing(method="fixed_amount", amount=100000) 
    
    signals = pd.Series(0, index=mock_price_data.index)
    signals.iloc[0] = 1 # Buy
    signals = signals.replace(0, np.nan).ffill().fillna(0) # Maintain signal
    
    engine.run(mock_price_data, signals)
    
    trades = engine.trades
    assert len(trades) >= 1
    
    # Price is ~100. Capital 1000. Max shares ~10.
    # If we tried to buy 1000 shares (amount 100000), we would be -99000 cash.
    # The fix should cap it at ~10.
    
    assert engine.position <= 10.5, f"Should not buy more than ~10 shares, bought {engine.position}"
    assert engine.current_capital >= 0, "Cash should not be negative"

def test_long_only_prevention(mock_price_data):
    """
    Test Case 6: Long Only Prevention
    Scenario: long_only=True, Position 0, Sell Signal.
    Expected: No trade (no shorting).
    """
    engine = BacktestEngine(initial_capital=10000, long_only=True)
    
    signals = pd.Series(0, index=mock_price_data.index)
    signals.iloc[0] = -1 # Sell (Short)
    signals = signals.replace(0, np.nan).ffill().fillna(0) # Maintain signal
    
    engine.run(mock_price_data, signals)
    
    trades = engine.trades
    assert len(trades) == 0, "Should not execute any trades (no shorting allowed)"
    assert engine.position == 0

def test_zero_price_handling():
    """
    Test Case 7: Zero Price Handling
    Scenario: Price is 0 on execution day.
    Expected: Should not execute trade.
    """
    dates = pd.date_range(start="2023-01-01", periods=3, freq="D")
    data = pd.DataFrame({
        "Open": [100.0, 100.0, 0.0], # Day 3 Open is 0
        "High": [105.0, 105.0, 0.0],
        "Low": [95.0, 95.0, 0.0],
        "Close": [100.0, 100.0, 0.0],
        "Volume": [1000, 1000, 0]
    }, index=dates)
    
    engine = BacktestEngine(initial_capital=10000)
    
    # Signal on Day 2 (Price 100) -> Execute Day 3 (Price 0)
    signals = pd.Series([0, 1, 0], index=dates) 
    
    engine.run(data, signals)
    
    trades = engine.trades
    # Should not have bought at 0
    assert len(trades) == 0

def test_extreme_signals():
    """
    Test Case 9: Extreme Signals
    Scenario: Signal is Inf or NaN.
    Expected: Should be treated as 0 or ignored.
    """
    dates = pd.date_range(start="2023-01-01", periods=3, freq="D")
    data = pd.DataFrame({
        "Open": [100.0, 100.0, 100.0],
        "High": [105.0, 105.0, 105.0],
        "Low": [95.0, 95.0, 95.0],
        "Close": [100.0, 100.0, 100.0],
        "Volume": [1000, 1000, 1000]
    }, index=dates)
    
    engine = BacktestEngine(initial_capital=10000)
    
    # Signal on Day 1 is Inf
    signals = pd.Series([np.inf, 0, 0], index=dates)
    
    # Should raise ValueError due to infinite values
    with pytest.raises(ValueError, match="Input data contains Infinite values"):
        engine.run(data, signals)

def test_empty_data_handling():
    """
    Test Case 8: Empty Data Handling
    Scenario: Empty DataFrame passed.
    Expected: Graceful exit, no trades.
    """
    data = pd.DataFrame()
    signals = pd.Series(dtype=float)
    
    engine = BacktestEngine()
    engine.run(data, signals)
    
    assert len(engine.trades) == 0
    assert len(engine.equity_curve) == 0
