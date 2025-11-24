import pytest
import numpy as np
from src.analytics.monte_carlo import run_monte_carlo_simulation

def test_simulation_shape():
    # Input: 50 trade returns
    trade_returns = [0.01] * 50 # 1% return each trade
    n_simulations = 100
    
    results = run_monte_carlo_simulation(trade_returns, n_simulations=n_simulations)
    
    curves = results['curves']
    # Shape should be (n_simulations, n_trades + 1) because we prepend initial capital
    assert curves.shape == (n_simulations, 51)
    
    # Check initial capital is preserved at index 0
    assert np.all(curves[:, 0] == 10000)

def test_worst_case_logic():
    # Input: Mix of gains and significant losses
    # [0.1, 0.1, -0.5, 0.1, -0.5]
    trade_returns = [0.1, 0.1, -0.5, 0.1, -0.5]
    n_simulations = 1000
    
    results = run_monte_carlo_simulation(trade_returns, n_simulations=n_simulations)
    
    p5_final = results['p5'][-1]
    p50_final = results['p50'][-1]
    p95_final = results['p95'][-1]
    
    # P5 (Worst 5%) should be less than P50 (Median)
    assert p5_final < p50_final
    
    # P95 (Best 5%) should be greater than P50
    assert p95_final > p50_final

def test_empty_input():
    results = run_monte_carlo_simulation([])
    assert results == {}

def test_simulation_sanity_check(capsys):
    # Input: trade_returns = [5, 5, 5] (Mistakenly entered as 5% -> 5.0 instead of 0.05)
    # New Logic: Should NOT auto-normalize, but should print a warning.
    trade_returns = [5, 5, 5]
    n_simulations = 10
    
    results = run_monte_carlo_simulation(trade_returns, n_simulations=n_simulations)
    
    # Check for warning
    captured = capsys.readouterr()
    assert "Warning: High returns detected" in captured.out
    
    # Check that it used RAW values (5.0 = 500%)
    # 10000 * 6 * 6 * 6 = 2,160,000
    final_equity = results['p50'][-1]
    assert final_equity > 2000000, f"Expected > 2M (raw 500% returns), got {final_equity}. Auto-normalization should be disabled."
