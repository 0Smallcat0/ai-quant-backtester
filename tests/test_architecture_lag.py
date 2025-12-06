import pytest
import pandas as pd
import numpy as np
from src.backtest_engine import BacktestEngine
from src.strategies.base import Strategy

class MockLagStrategy(Strategy):
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df['signal'] = 0.0
        # Generate a BUY signal on a specific date
        # We want to verify that if signal is on Day T, trade is on Day T+1
        if '2023-01-02' in df.index:
            df.loc['2023-01-02', 'signal'] = 1.0
        return df

class MockSafeRollingStrategy(Strategy):
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        # Use the new safe_rolling method
        # We expect this to fail if the method is not implemented yet
        try:
            df['ma'] = self.safe_rolling('close', 2, 'mean')
        except AttributeError:
            # Fallback for initial test run before implementation
            df['ma'] = 0.0
        df['signal'] = 0.0
        return df

@pytest.fixture
def sample_data():
    dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
    data = pd.DataFrame({
        'open': [100, 101, 102, 103, 104],
        'high': [105, 106, 107, 108, 109],
        'low': [95, 96, 97, 98, 99],
        'close': [100, 102, 104, 106, 108],
        'volume': [1000, 1000, 1000, 1000, 1000]
    }, index=dates)
    return data

def test_signal_lag_enforcement(sample_data):
    """
    Case A: Signal Lag Enforcement
    Verify that a signal generated on Day T results in a trade on Day T+1.
    """
    engine = BacktestEngine(initial_capital=10000)
    strategy = MockLagStrategy()
    signals = strategy.generate_signals(sample_data)['signal']
    
    engine.run(sample_data, signals)
    
    trades = engine.trades
    assert len(trades) > 0, "Should have executed at least one trade"
    
    first_trade = trades[0]
    
    # Signal was on 2023-01-02 (Day T)
    # Trade should be on 2023-01-03 (Day T+1)
    # If it traded on 2023-01-02, it's a look-ahead bias (instant execution)
    
    assert first_trade.entry_date == pd.Timestamp('2023-01-03'), \
        f"Trade executed on {first_trade.entry_date}, expected 2023-01-03 (T+1)"

def test_safe_rolling_logic():
    """
    Case B: Safe Rolling Logic
    Verify that safe_rolling uses shifted data.
    """
    # Create a dummy strategy instance to access the method
    strategy = MockSafeRollingStrategy()
    
    dates = pd.date_range(start='2023-01-01', periods=4, freq='D')
    data = pd.DataFrame({
        'close': [1.0, 2.0, 3.0, 4.0]
    }, index=dates)
    
    strategy.data = data
    
    # We need to implement safe_rolling in the base class for this to work.
    # But for TDD, we can check if the method exists and behaves as expected.
    # Since we haven't implemented it yet, this test will fail or error out if we try to call it.
    # So we will check for the attribute error or incorrect calculation if we were to mock it.
    
    # Ideally, we want to call strategy.safe_rolling('close', 2)
    # Expected behavior:
    # Index 0 (1.0): NaN (Shift 1 -> NaN)
    # Index 1 (2.0): NaN (Shift 1 -> 1.0, Rolling 2 -> NaN)
    # Index 2 (3.0): 1.5 (Shift 1 -> 2.0, Previous Shifted -> 1.0. Mean(1.0, 2.0) = 1.5)
    # Wait, let's trace:
    # Data: [1, 2, 3, 4]
    # Shift(1): [NaN, 1, 2, 3]
    # Rolling(2) on Shifted:
    # i=0: NaN
    # i=1: NaN (needs 2 values, has NaN, 1) -> NaN? Or if min_periods=1? Standard rolling(2) needs 2.
    # i=2: Mean(1, 2) = 1.5. The value at i=2 (3.0) is NOT used.
    # i=3: Mean(2, 3) = 2.5. The value at i=3 (4.0) is NOT used.
    
    if not hasattr(strategy, 'safe_rolling'):
        pytest.fail("Strategy class missing safe_rolling method")
        
    result = strategy.safe_rolling('close', 2, 'mean')
    
    # Check value at index 2 ('2023-01-03')
    # Original close is 3.0
    # We expect mean of previous two closes: 1.0 and 2.0 -> 1.5
    
    val_at_index_2 = result.iloc[2]
    assert val_at_index_2 == 1.5, f"Expected 1.5, got {val_at_index_2}. Look-ahead leaked?"
    
    # Check value at index 3 ('2023-01-04')
    # Original close is 4.0
    # We expect mean of previous two closes: 2.0 and 3.0 -> 2.5
    val_at_index_3 = result.iloc[3]
    assert val_at_index_3 == 2.5, f"Expected 2.5, got {val_at_index_3}"
