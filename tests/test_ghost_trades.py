import pytest
import pandas as pd
import numpy as np
from src.backtest_engine import BacktestEngine
from src.config.settings import DEFAULT_MIN_COMMISSION

class TestGhostTrades:
    def setup_method(self):
        # Create a simple dataset: Price flat at 100
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        self.data = pd.DataFrame({
            'open': [100.0] * 10,
            'high': [101.0] * 10,
            'low': [99.0] * 10,
            'close': [100.0] * 10,
            'volume': [1000] * 10
        }, index=dates)
        
        # Mock strategy that returns a specific signal
        self.mock_strategy_class = type('MockStrategy', (object,), {
            'generate_signals': lambda self, df: pd.Series([0.0] * len(df), index=df.index)
        })

    def test_case_a_minimum_commission_kill(self):
        """
        Case A: Minimum Commission Kill
        Simulate a strategy: Open 1 share, Price unchanged, Close 1 share.
        Assert: Equity drops by exactly 2 * MIN_COMMISSION (entry + exit).
        """
        # Create a signal that buys 1 share on day 1 and sells on day 5
        # Note: In Target-Delta logic, signal is target exposure.
        # To buy 1 share at price 100, target exposure is roughly 100 / 10000 = 0.01 (assuming 10k capital)
        # But let's force a specific small signal.
        
        signals = pd.Series([0.0] * 10, index=self.data.index)
        # Day 0 signal -> Day 1 execution
        signals.iloc[0] = 0.01  # Target 1% exposure (approx 1 share if capital=10000, price=100)
        signals.iloc[4] = 0.0   # Close position
        
        strategy = self.mock_strategy_class()
        strategy.generate_signals = lambda df: signals
        
        # Force min commission to be significant (e.g. 5.0) for this test to be clear
        test_min_comm = 5.0
        engine = BacktestEngine(initial_capital=10000.0, min_commission=test_min_comm, slippage=0.0)
        
        # Run backtest
        # engine.run expects signals as a Series, not a strategy object
        engine.run(self.data, signals)
        
        # Check trades
        trades = engine.trades
        assert len(trades) >= 2, "Should have at least entry and exit trades"
        
        # Calculate expected commission cost
        # If MIN_COMMISSION is 5.0, then 2 trades = $10.0 loss
        # Price didn't change, so PnL from price action is 0.
        
        initial_equity = engine.equity_curve[0]['equity']
        final_equity = engine.equity_curve[-1]['equity']
        
        # We expect loss solely due to commission
        expected_loss = len(trades) * test_min_comm
        
        # Allow for small floating point diffs
        assert abs((initial_equity - final_equity) - expected_loss) < 1e-5, \
            f"Equity should drop by exactly commission cost. Drop: {initial_equity - final_equity}, Expected: {expected_loss}"

    def test_case_b_tiny_exposure_detection(self):
        """
        Case B: Tiny Exposure
        Simulate Exposure < 1% (signal < 0.01) but > 0.
        Assert: 
        - Before fix: Trades happen (and lose money to commission).
        - After fix: No trades happen (signal filtered).
        """
        # Signal is very small, e.g., 0.0001
        signals = pd.Series([0.0] * 10, index=self.data.index)
        signals.iloc[0] = 0.0001 
        signals.iloc[4] = 0.0
        
        strategy = self.mock_strategy_class()
        strategy.generate_signals = lambda df: signals
        
        engine = BacktestEngine(initial_capital=10000.0)
        engine.run(self.data, signals)
        
        trades = engine.trades
        
        # Ideally, we want to assert that NO trades happen if we implement the fix.
        # But for "Diagnose" phase, we might expect trades to happen if the fix isn't there yet.
        # The user request says: "Assert: System can identify and warn..." 
        # But for the unit test of the FIX, we want to assert 0 trades.
        
        # Let's write the test expecting the FIX (TDD).
        # So we expect 0 trades for this tiny signal.
        assert len(trades) == 0, f"Tiny signal {signals.iloc[0]} should be filtered out, but got {len(trades)} trades."
