import pytest
import pandas as pd
import numpy as np
from src.backtest_engine import BacktestEngine
from src.config.settings import settings

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
        signals = pd.Series([0.0] * 10, index=self.data.index)
        # Day 0 signal -> Day 1 execution
        signals.iloc[0] = 0.01  # Target 1% exposure
        signals.iloc[4] = 0.0   # Close position
        
        strategy = self.mock_strategy_class()
        strategy.generate_signals = lambda df: signals
        
        # Force min commission to be significant (e.g. 5.0) for this test to be clear
        test_min_comm = 5.0
        engine = BacktestEngine(initial_capital=10000.0, min_commission=test_min_comm, slippage=0.0)
        
        # Run backtest
        engine.run(self.data, signals)
        
        # Check trades
        trades = engine.trades
        assert len(trades) >= 2, "Should have at least entry and exit trades"
        
        initial_equity = engine.equity_curve.iloc[0]['equity']
        final_equity = engine.equity_curve.iloc[-1]['equity']
        
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
        
        engine = BacktestEngine(initial_capital=settings.INITIAL_CAPITAL)
        engine.run(self.data, signals)
        
        trades = engine.trades
        
        # Expect 0 trades for this tiny signal.
        assert len(trades) == 0, f"Tiny signal {signals.iloc[0]} should be filtered out, but got {len(trades)} trades."
