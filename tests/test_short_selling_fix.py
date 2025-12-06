import pytest
import collections
from src.analytics.performance import calculate_round_trip_returns

# Mock Trade Object
class MockTrade:
    def __init__(self, type, entry_price, quantity, entry_equity=10000.0):
        self.type = type
        self.entry_price = float(entry_price)
        self.quantity = float(quantity)
        self.entry_equity = float(entry_equity)

def test_short_selling_loss():
    """
    Case A: Short Loss
    Trade 1: SELL 1 unit @ 100
    Trade 2: BUY 1 unit @ 110
    Result: Loss of 10 (plus commission if any).
    """
    trades = [
        MockTrade('SELL', 100.0, 1.0, entry_equity=1000.0),
        MockTrade('BUY', 110.0, 1.0, entry_equity=1000.0) # Equity doesn't matter for closing trade in this logic usually, but we provide it.
    ]
    
    # Commission = 0 for simplicity first
    returns = calculate_round_trip_returns(trades, commission_rate=0.0)
    
    assert len(returns) == 1, f"Expected 1 return, got {len(returns)}"
    # PnL = (100 - 110) * 1 = -10
    # Return = -10 / 1000 = -0.01
    assert returns[0] == pytest.approx(-0.01), f"Expected -0.01, got {returns[0]}"

def test_short_selling_profit():
    """
    Case B: Short Profit
    Trade 1: SELL 1 unit @ 100
    Trade 2: BUY 1 unit @ 90
    Result: Profit of 10.
    """
    trades = [
        MockTrade('SELL', 100.0, 1.0, entry_equity=1000.0),
        MockTrade('BUY', 90.0, 1.0, entry_equity=1000.0)
    ]
    
    returns = calculate_round_trip_returns(trades, commission_rate=0.0)
    
    assert len(returns) == 1
    # PnL = (100 - 90) * 1 = 10
    # Return = 10 / 1000 = 0.01
    assert returns[0] == pytest.approx(0.01)

def test_mixed_fifo_execution():
    """
    Case C: Mixed FIFO
    1. BUY 1 @ 100 (Long Open)
    2. SELL 1 @ 110 (Long Close) -> Profit 10
    3. SELL 1 @ 110 (Short Open)
    4. BUY 1 @ 100 (Short Close) -> Profit 10
    
    Note: In a real engine, step 2 and 3 might be a single SELL 2 @ 110 command if flipping.
    But here we test the matching logic with explicit trades.
    """
    trades = [
        MockTrade('BUY', 100.0, 1.0, entry_equity=1000.0),  # Long Open
        MockTrade('SELL', 110.0, 1.0, entry_equity=1000.0), # Long Close
        MockTrade('SELL', 110.0, 1.0, entry_equity=1000.0), # Short Open
        MockTrade('BUY', 100.0, 1.0, entry_equity=1000.0)   # Short Close
    ]
    
    returns = calculate_round_trip_returns(trades, commission_rate=0.0)
    
    assert len(returns) == 2
    # Trade 1: (110 - 100) = 10. Ret = 0.01
    # Trade 2: (110 - 100) = 10. Ret = 0.01 (Short from 110 down to 100)
    
    assert returns[0] == pytest.approx(0.01)
    assert returns[1] == pytest.approx(0.01)

def test_short_selling_with_commission():
    """
    Test commission impact on short selling.
    SELL 1 @ 100, BUY 1 @ 90. Comm 0.001 (0.1%)
    Gross PnL = 10
    Comm = (100 * 1 * 0.001) + (90 * 1 * 0.001) = 0.1 + 0.09 = 0.19
    Net PnL = 9.81
    Return = 9.81 / 1000 = 0.00981
    """
    trades = [
        MockTrade('SELL', 100.0, 1.0, entry_equity=1000.0),
        MockTrade('BUY', 90.0, 1.0, entry_equity=1000.0)
    ]
    
    returns = calculate_round_trip_returns(trades, commission_rate=0.001)
    
    assert len(returns) == 1
    assert returns[0] == pytest.approx(0.00981)
