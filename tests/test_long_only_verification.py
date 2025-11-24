import pytest
import pandas as pd
import numpy as np
from src.backtest_engine import BacktestEngine

def create_downtrend_data():
    """Creates a synthetic price series with a clear downtrend (100 -> 50)."""
    dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
    prices = np.linspace(100, 50, 10)
    data = pd.DataFrame({
        "open": prices,
        "high": prices + 1,
        "low": prices - 1,
        "close": prices,
        "volume": 1000
    }, index=dates)
    return data

def test_long_only_vs_allow_short_divergence():
    """
    Mathematical Proof:
    Verifies that Long-Only and Allow-Short modes produce DIFFERENT results
    given the same 'Always Short' signal in a downtrend.
    """
    data = create_downtrend_data()
    
    # Signal = -1.0 (Always Short)
    signals = pd.Series(-1.0, index=data.index)
    
    # ---------------------------------------------------------
    # Scenario A: Long Only
    # Expectation: No trades, PnL = 0 (Signal -1.0 -> 0.0)
    # ---------------------------------------------------------
    engine_long = BacktestEngine(initial_capital=10000, long_only=True)
    engine_long.run(data, signals)
    
    final_equity_long = engine_long.equity_curve[-1]["equity"]
    trades_long = len(engine_long.trades)
    
    print(f"\n[Long Only] Final Equity: {final_equity_long}, Trades: {trades_long}")
    
    # Assertions for Long Only
    assert trades_long == 0, "Long-Only engine should NOT execute any trades on Short signals."
    assert final_equity_long == 10000, "Long-Only engine should have flat equity (no PnL)."

    # ---------------------------------------------------------
    # Scenario B: Allow Short
    # Expectation: Short trades executed, Positive PnL (Shorting downtrend)
    # ---------------------------------------------------------
    engine_short = BacktestEngine(initial_capital=10000, long_only=False)
    engine_short.run(data, signals)
    
    final_equity_short = engine_short.equity_curve[-1]["equity"]
    trades_short = len(engine_short.trades)
    
    print(f"[Allow Short] Final Equity: {final_equity_short}, Trades: {trades_short}")
    
    # Assertions for Allow Short
    assert trades_short > 0, "Allow-Short engine MUST execute trades on Short signals."
    assert final_equity_short > 10000, "Shorting a downtrend should be profitable (ignoring massive slippage/commissions)."
    
    # ---------------------------------------------------------
    # Proof of Divergence
    # ---------------------------------------------------------
    assert final_equity_long != final_equity_short, "Long-Only and Allow-Short results MUST differ."
