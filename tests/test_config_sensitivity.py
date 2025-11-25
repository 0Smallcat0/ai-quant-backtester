import pytest
import pandas as pd
from src.backtest_engine import BacktestEngine
from src.config.settings import DEFAULT_INITIAL_CAPITAL

class TestConfigSensitivity:
    def test_slippage_sensitivity(self):
        """
        Verify that changing slippage actually affects the backtest result.
        This ensures the parameter is correctly wired from the init to the execution logic.
        """
        # Create dummy data
        dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
        data = pd.DataFrame({
            "open": [100, 101, 102, 103, 104, 105, 104, 103, 102, 101],
            "close": [101, 102, 103, 104, 105, 104, 103, 102, 101, 100],
            "high": [105] * 10,
            "low": [95] * 10,
            "volume": [1000] * 10
        }, index=dates)
        
        # Create signals: Buy at index 1, Sell at index 5
        signals = pd.Series(0, index=dates)
        signals.iloc[1] = 1  # Buy
        signals.iloc[5] = 0  # Sell (Flat)
        
        # Run with Zero Slippage
        engine_zero = BacktestEngine(initial_capital=10000, slippage=0.0, commission_rate=0.0)
        engine_zero.run(data, signals)
        equity_zero = engine_zero.equity_curve[-1]['equity']
        
        # Run with Huge Slippage (50%)
        # Buy at 102 (Open of index 2 due to lag), Price = 102 * 1.5 = 153
        # Sell at 104 (Open of index 6 due to lag), Price = 104 * 0.5 = 52
        # Loss should be massive
        engine_huge = BacktestEngine(initial_capital=10000, slippage=0.5, commission_rate=0.0)
        engine_huge.run(data, signals)
        equity_huge = engine_huge.equity_curve[-1]['equity']
        
        print(f"Equity Zero Slippage: {equity_zero}")
        print(f"Equity Huge Slippage: {equity_huge}")
        
        assert equity_zero != equity_huge, "Slippage parameter has no effect on backtest results!"
        assert equity_huge < equity_zero, "Higher slippage should result in lower equity."

if __name__ == "__main__":
    t = TestConfigSensitivity()
    t.test_slippage_sensitivity()
    print("Test Passed!")
