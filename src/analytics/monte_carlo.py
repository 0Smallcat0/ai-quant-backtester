import numpy as np
import pandas as pd

def run_monte_carlo_simulation(trade_returns: list, n_simulations: int = 1000, initial_capital: float = 10000) -> dict:
    """
    Run Bootstrap Resampling Monte Carlo Simulation.
    
    Args:
        trade_returns: List of percentage returns per trade (e.g. 0.01 for 1%).
        n_simulations: Number of simulation runs.
        initial_capital: Starting capital for the curves.
        
    Returns:
        Dictionary containing:
        - curves: np.array of shape (n_simulations, n_trades + 1)
        - p5, p50, p95: np.array of shape (n_trades + 1,)
        - stats: dict with VaR, Median Drawdown etc.
    """
    returns = np.array(trade_returns, dtype=float)
    n_trades = len(returns)
    
    if n_trades < 30:
        print("Warning: Small sample size (<30 trades); Monte Carlo simulation may be unreliable.")

    
    if n_trades == 0:
        return {}
    
    # Generate random indices for resampling with replacement
    # Shape: (n_simulations, n_trades)
    random_indices = np.random.randint(0, n_trades, size=(n_simulations, n_trades))
    
    # Select returns based on indices
    simulated_returns = returns[random_indices]
    
    # 1. Auto-Normalization: Check if returns are likely in percentage format (e.g. 5.0 instead of 0.05)
    # Heuristic: If mean absolute value > 1.0 AND 95th percentile > 0.5, assume it's percentage.
    # We only warn the user, we do not auto-correct to avoid destroying high-return strategies (e.g. 200% return).
    mean_abs = np.mean(np.abs(simulated_returns))
    p95_abs = np.percentile(np.abs(simulated_returns), 95)
    
    if mean_abs > 1.0 and p95_abs > 0.5:
        print(f"Warning: High returns detected (Mean Abs={mean_abs:.2f}, P95={p95_abs:.2f}). Assuming raw values (e.g. 2.0 = 200%). If these are percentages (2.0 = 2%), please divide by 100 before passing.")

    # 2. Loss Capping: Ensure no single trade loss is worse than -100% (-1.0)
    # This prevents mathematical errors or negative equity in simple compounding
    capped_losses_count = 0
    capped_mask = simulated_returns < -1.0
    if np.any(capped_mask):
        capped_losses_count = np.sum(capped_mask)
        simulated_returns = np.maximum(simulated_returns, -1.0)
    
    # Calculate cumulative returns (Equity Curves)
    # We start with 1.0 and multiply by (1 + r)
    # cumprod along axis 1
    growth_factors = 1 + simulated_returns
    cumulative_growth = np.cumprod(growth_factors, axis=1)
    
    # Scale by initial capital
    simulated_curves = cumulative_growth * initial_capital
    
    # Prepend initial capital (Time 0)
    start_col = np.full((n_simulations, 1), initial_capital)
    simulated_curves = np.hstack((start_col, simulated_curves))
    
    # Calculate Percentiles per step (for plotting the cone/cloud)
    p5 = np.percentile(simulated_curves, 5, axis=0)
    p50 = np.percentile(simulated_curves, 50, axis=0)
    p95 = np.percentile(simulated_curves, 95, axis=0)
    
    # Calculate Stats
    final_values = simulated_curves[:, -1]
    
    # VaR 95% (Absolute Value at Risk from Initial Capital)
    # If 5th percentile is 9000 and initial is 10000, VaR is 1000.
    # If 5th percentile is 11000, VaR is 0 (no loss expected at 95%).
    # Requirement says "預期的最差虧損".
    p5_final = np.percentile(final_values, 5)
    var_95_amount = initial_capital - p5_final
    
    # Median Drawdown
    # Calculate Max Drawdown for EACH simulation, then take median.
    # Max Drawdown calculation for a matrix:
    # cummax along axis 1
    cummax = np.maximum.accumulate(simulated_curves, axis=1)
    drawdowns = (simulated_curves - cummax) / cummax
    max_drawdowns = np.min(drawdowns, axis=1) # Min because drawdowns are negative
    median_drawdown = np.median(max_drawdowns)
    
    return {
        "curves": simulated_curves,
        "p5": p5,
        "p50": p50,
        "p95": p95,
        "final_values": final_values,
        "var_95_amount": var_95_amount,
        "median_drawdown": median_drawdown,
        "median_drawdown": median_drawdown,
        "p5_final": p5_final,
        "capped_losses": capped_losses_count
    }
