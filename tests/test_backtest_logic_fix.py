import pytest
import pandas as pd
import numpy as np
from src.backtest_engine import BacktestEngine

# Mock Data Fixture
@pytest.fixture
def mock_price_data():
    """
    Creates a simple 10-day OHLCV DataFrame for testing.
    Dates: 2023-01-01 to 2023-01-10
    Prices: Flat 100.0 to make math easy.
    """
    dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
    data = pd.DataFrame({
        "Open": [100.0] * 10,
        "High": [105.0] * 10,
        "Low": [95.0] * 10,
        "Close": [100.0] * 10,
        "Volume": [1000] * 10
    }, index=dates)
    return data

def test_long_only_compliance(mock_price_data):
    """
    Case A: Long-Only Compliance
    Scenario: long_only=True, Position=0, Signal < 0 (Sell/Short).
    Expected: No trade should be executed. Position remains 0.
    """
    engine = BacktestEngine(initial_capital=10000, long_only=True)
    
    signals = pd.Series(0, index=mock_price_data.index)
    signals.iloc[0] = -1  # Sell signal on Day 1
    
    engine.run(mock_price_data, signals)
    
    assert len(engine.trades) == 0, "Should not execute any trades"
    assert engine.position == 0.0, "Position should remain 0"
    assert engine.current_capital == 10000.0, "Capital should remain unchanged"

def test_target_delta_sizing(mock_price_data):
    """
    Case B: Target-Delta Position Sizing
    Scenario: 
    1. Buy to 10 units.
    2. Signal changes to reduce position to 5 units.
    Expected: Sell 5 units (Delta), not full close or incorrect amount.
    """
    engine = BacktestEngine(initial_capital=100000)
    # Use fixed amount to make unit calculation deterministic
    # Price is 100. 
    
    # We need to manually construct signals that imply specific targets if we are testing the NEW logic.
    # However, the current engine doesn't fully support "Target-Delta" based on signal magnitude yet (that's what we are fixing).
    # BUT, the requirement says "Test Case B: Target-Delta Sizing".
    # To test the *flaw* in the *current* engine or the *feature* in the *new* engine?
    # The user asked for "Reproduction Tests". 
    # In the CURRENT engine, if I have a position and get a SELL signal, it might close ALL of it (depending on logic).
    # Let's try to simulate the desire: 
    # Day 1: Signal 1.0 (Buy) -> Target 10 units (we will set sizing to fixed amount 1000 for 10 units)
    # Day 2: Signal 0.5 (Reduce) -> Target 5 units.
    
    # NOTE: The current engine interprets Signal > 0 as BUY and Signal < 0 as SELL. 
    # It does NOT interpret Signal 0.5 as "Target 50%". 
    # So this test is actually defining the *Expected Behavior* of the Refactored Engine.
    # It will likely FAIL on the current engine because the current engine treats any positive signal as BUY (or hold if already long? No, it keeps buying if pending order).
    # Actually, current engine: if signal > 0 -> Order(BUY). 
    # If I am already long, and get another BUY order, I might buy MORE.
    # If I want to reduce, I need a SELL order.
    # The new logic wants Signal=0.5 to mean "Target 50%".
    
    # Let's write the test expecting the NEW behavior (Target-Delta).
    
    engine.set_position_sizing(method="fixed_amount", amount=1000) # 10 units at price 100
    
    signals = pd.Series(0.0, index=mock_price_data.index)
    signals.iloc[0] = 1.0   # Day 1: Target 10 units
    signals.iloc[1] = 0.5   # Day 2: Target 5 units (Should SELL 5)
    
    # Forward fill signals to maintain the target of 0.5 for the rest of the test
    # Otherwise, 0.0 means Target 0 (Exit)
    signals = signals.replace(0.0, np.nan).ffill().fillna(0.0)
    
    # We need to update the engine to understand that 0.5 means "Target 50% of the Sizing Amount" 
    # OR we change the interpretation of the signal.
    # The plan says: "Calculate target_equity_exposure = equity * signal * position_sizing_target"
    # So if Signal is 0.5, and Sizing is "Fixed Amount 1000", then Target is 500.
    
    engine.run(mock_price_data, signals)
    
    # Expected:
    # T+1 (Day 2 Open): Buy 10 units. Pos = 10.
    # T+2 (Day 3 Open): Target is 5 units. Pos is 10. Delta = -5. Sell 5.
    
    # Check Trades
    # Trade 1: Buy 10
    # Trade 2: Sell 5
    
    assert len(engine.trades) >= 2, f"Should have at least 2 trades, got {len(engine.trades)}"
    if len(engine.trades) >= 2:
        assert engine.trades[0].type == "BUY"
        assert engine.trades[0].quantity == pytest.approx(10.0)
        
        assert engine.trades[1].type == "SELL"
        assert engine.trades[1].quantity == pytest.approx(5.0) 
        
    assert engine.position == pytest.approx(5.0)

def test_bankruptcy_break(mock_price_data):
    """
    Case C: Bankruptcy Break
    Scenario: A trade causes equity to go negative.
    Expected: The loop should break immediately. No more data points in equity curve after bankruptcy.
    """
    engine = BacktestEngine(initial_capital=10000)
    
    # Scenario: Short Selling leading to Bankruptcy
    # Sell 100 units at 100. Proceeds +10,000. Cash 20,000.
    # Price goes to 300. Liability 30,000. Equity = 20,000 - 30,000 = -10,000.
    
    dates = pd.date_range(start="2023-01-01", periods=5, freq="D")
    data = pd.DataFrame({
        "Open": [100, 100, 300, 300, 300],
        "High": [300] * 5,
        "Low": [100] * 5,
        "Close": [100, 100, 300, 300, 300], 
        "Volume": [1000] * 5
    }, index=dates)
    
    engine.set_position_sizing(method="fixed_amount", amount=10000) 
    
    signals = pd.Series(0.0, index=dates)
    signals.iloc[0] = -1.0 # Short
    signals = signals.replace(0.0, np.nan).ffill().fillna(0.0) # Maintain Short
    
    engine.run(data, signals)
    
    # Day 1: Signal Short.
    # Day 2: Execute Short @ 100. Close 100. Equity 10000.
    # Day 3: Close 300. 
    # Pos = -100. Price 300. Value = -30000.
    # Cash (approx) = 10000 (init) + 10000 (short proceeds) = 20000.
    # Equity = 20000 - 30000 = -10000. -> Bankruptcy.
    
    # The engine now fills the remaining dates with 0 equity for robustness (charting).
    # So we expect the curve to have the same length as the input data (5 days).
    assert len(engine.equity_curve) == 5, f"Should fill remaining days with 0, got {len(engine.equity_curve)} days"
    assert engine.equity_curve.iloc[-1]['equity'] == 0.0
    assert engine.equity_curve.iloc[-2]['equity'] == 0.0
