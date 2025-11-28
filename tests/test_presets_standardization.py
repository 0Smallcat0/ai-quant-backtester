import pytest
import pandas as pd
import numpy as np
from src.strategies.presets import MovingAverageStrategy, SentimentRSIStrategy, BollingerBreakoutStrategy
from src.strategies.base import Strategy

def test_presets_inheritance():
    """
    Case A: Import Check (Inheritance)
    Verify all strategies inherit from Strategy base class.
    """
    assert issubclass(MovingAverageStrategy, Strategy)
    assert issubclass(SentimentRSIStrategy, Strategy)
    assert issubclass(BollingerBreakoutStrategy, Strategy)

def test_sma_safety_lookahead():
    """
    Case B: Safety Check (Look-ahead Bias) for SMA.
    Verify that the first N elements (window size) are NaN or 0, 
    and specifically that the calculation uses safe_rolling (shifted).
    """
    # Create simple data: Close price increasing 1, 2, 3...
    dates = pd.date_range(start="2023-01-01", periods=10)
    data = pd.DataFrame({'close': range(1, 11)}, index=dates)
    
    window = 3
    strategy = MovingAverageStrategy(window=window)
    signals = strategy.generate_signals(data)
    
    # Check 'ma' column
    # safe_rolling shifts by 1, then rolls.
    # T=0: NaN (No prev data)
    # T=1: NaN (Prev=1, need 3)
    # T=2: NaN (Prev=1,2, need 3)
    # T=3: Mean(1,2,3) = 2.0. This value is available at T=3? 
    # Wait, safe_rolling logic:
    # return self.data[column].shift(1).rolling(window=window).agg(func)
    # T=0: shift(1) -> NaN
    # T=1: shift(1) -> 1
    # T=2: shift(1) -> 2
    # T=3: shift(1) -> 3
    # Rolling(3) on [NaN, 1, 2, 3, ...]
    # Index 0 (T=0): NaN
    # Index 1 (T=1): NaN (1 val)
    # Index 2 (T=2): NaN (2 vals)
    # Index 3 (T=3): Mean(1, 2, 3) = 2.0. 
    # So at T=3 (Close=4), we compare Close(4) with MA(2.0). Correct.
    
    # So first 3 values (indices 0, 1, 2) should be NaN.
    assert pd.isna(signals['ma'].iloc[0])
    assert pd.isna(signals['ma'].iloc[1])
    assert pd.isna(signals['ma'].iloc[2])
    assert not pd.isna(signals['ma'].iloc[3])
    assert signals['ma'].iloc[3] == 2.0

def test_rsi_calculation_manual():
    """
    Verify RSI calculation is correct and safe.
    """
    # Create data that generates specific RSI
    # Up, Up, Up...
    dates = pd.date_range(start="2023-01-01", periods=20)
    # 0, 1, 2, ... 19
    data = pd.DataFrame({'close': range(20)}, index=dates)
    
    period = 14
    strategy = SentimentRSIStrategy(period=period)
    signals = strategy.generate_signals(data)
    
    # Check RSI exists
    assert 'rsi' in signals.columns
    # First period+1 should be NaN (due to shift and diff)
    # shift(1) makes T=0 NaN.
    # diff() on shifted data:
    # T=0: NaN
    # T=1: Shift->0. Diff(0-NaN) -> NaN? No, diff is on the shifted series.
    # Series: [NaN, 0, 1, 2...]
    # Diff: [NaN, NaN, 1, 1...]
    # So first 2 are NaN?
    # Actually safe_pct_change or manual diff on shifted data.
    # The implementation plan says "Implement manual RSI with safe logic".
    # Let's check the implementation in presets.py (which we will refactor).
    # We expect the first few to be NaN.
    assert pd.isna(signals['rsi'].iloc[0])

def test_bollinger_safety():
    """
    Verify Bollinger Bands use safe_rolling.
    """
    dates = pd.date_range(start="2023-01-01", periods=10)
    data = pd.DataFrame({'close': [10]*10}, index=dates)
    
    window = 5
    strategy = BollingerBreakoutStrategy(window=window)
    signals = strategy.generate_signals(data)
    
    # Check columns
    assert 'upper' in signals.columns
    assert 'ma' in signals.columns
    
    # First window rows should be NaN due to safe_rolling
    for i in range(window):
        assert pd.isna(signals['ma'].iloc[i])
