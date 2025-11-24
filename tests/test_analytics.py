import pytest
import pandas as pd
import numpy as np
from src.analytics.performance import calculate_cagr, calculate_max_drawdown, calculate_sharpe_ratio, calculate_win_rate

def test_calculate_cagr():
    # Start 100, End 120, 1 Year -> 20%
    start_value = 100
    end_value = 120
    years = 1
    cagr = calculate_cagr(start_value, end_value, years)
    assert cagr == pytest.approx(0.20, abs=0.001)

    # Start 100, End 144, 2 Years -> 20% (1.2 * 1.2 = 1.44)
    cagr_2 = calculate_cagr(100, 144, 2)
    assert cagr_2 == pytest.approx(0.20, abs=0.001)

def test_cagr_bankruptcy():
    # Bankruptcy case: End value is negative
    start_value = 10000
    end_value = -500
    years = 1
    cagr = calculate_cagr(start_value, end_value, years)
    assert cagr == -1.0

def test_cagr_short_duration():
    # Short duration case: 0 days (years=0)
    start_value = 10000
    end_value = 10500
    years = 0
    cagr = calculate_cagr(start_value, end_value, years)
    assert cagr == 0.0

def test_calculate_max_drawdown():
    # [100, 120, 90, 110]
    # Peak 120, Trough 90 -> Drawdown (90-120)/120 = -0.25
    equity_curve = pd.Series([100, 120, 90, 110])
    mdd = calculate_max_drawdown(equity_curve)
    assert mdd == pytest.approx(-0.25, abs=0.001)

    # No drawdown
    equity_curve_up = pd.Series([100, 110, 120, 130])
    mdd_up = calculate_max_drawdown(equity_curve_up)
    assert mdd_up == 0.0

def test_calculate_sharpe_ratio():
    # Daily Returns: [0.01, 0.01, 0.01, ...]
    # Mean = 0.01, Std = 0 (approx) -> Sharpe should be very high or handle div by zero if std is 0
    # Let's use a sequence with some variance
    returns = pd.Series([0.01, 0.02, 0.01, -0.005, 0.015])
    sharpe = calculate_sharpe_ratio(returns)
    assert sharpe > 0

    # Negative returns
    returns_neg = pd.Series([-0.01, -0.02, -0.01])
    sharpe_neg = calculate_sharpe_ratio(returns_neg)
    assert sharpe_neg < 0

def test_calculate_win_rate():
    # 2 Wins, 2 Losses -> 50%
    trades = [
        {'pnl': 10},
        {'pnl': 20},
        {'pnl': -5},
        {'pnl': -10}
    ]
    # Assuming the function takes a list of trades or a DataFrame
    # Let's assume it takes a DataFrame or list of dicts with 'pnl' or similar
    # Adjusting based on BacktestEngine Trade object structure or just PnL list
    # The requirement says "Win Rate: 獲利交易次數 / 總交易次數"
    # Let's pass a list of PnL values for simplicity in this unit test, or a DataFrame
    
    pnl_series = pd.Series([10, 20, -5, -10])
    win_rate = calculate_win_rate(pnl_series)
    assert win_rate == 0.5

    # All wins
    pnl_all_wins = pd.Series([10, 20])
    assert calculate_win_rate(pnl_all_wins) == 1.0

    # No trades
    assert calculate_win_rate(pd.Series([], dtype=float)) == 0.0
