import pytest
import pandas as pd
import numpy as np
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analytics.performance import calculate_sharpe_ratio

def test_sharpe_flat_curve():
    """Case A: Flat Curve (Zero Volatility) -> Sharpe 0.0"""
    # All returns are 0
    returns = pd.Series([0.0] * 100)
    sharpe = calculate_sharpe_ratio(returns)
    
    assert sharpe == 0.0, f"Expected Sharpe 0.0 for flat curve, got {sharpe}"
    assert not np.isnan(sharpe), "Sharpe should not be NaN"

def test_sharpe_constant_positive_returns():
    """Case B: Constant Positive Returns (Zero Volatility) -> Sharpe 0.0"""
    # All returns are 0.01
    returns = pd.Series([0.01] * 100)
    sharpe = calculate_sharpe_ratio(returns)
    
    # Std dev is 0, so division by zero occurs. Should return 0.0 safe guard.
    assert sharpe == 0.0, f"Expected Sharpe 0.0 for constant returns, got {sharpe}"
    assert not np.isnan(sharpe), "Sharpe should not be NaN"

def test_sharpe_normal_case():
    """Case C: Normal Case -> Sharpe > 0"""
    # Random returns
    np.random.seed(42)
    returns = pd.Series(np.random.normal(0.001, 0.02, 100))
    sharpe = calculate_sharpe_ratio(returns)
    
    assert isinstance(sharpe, float)
    assert not np.isnan(sharpe)
    # With mean ~0.001 and std ~0.02, sharpe should be roughly sqrt(252) * (0.001/0.02) ~ 15.8 * 0.05 ~ 0.8
    # Just check it's not 0 and not NaN
    assert sharpe != 0.0
