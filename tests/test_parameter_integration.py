import pytest
import pandas as pd
from src.backtest_engine import BacktestEngine

class TestParameterIntegration:
    """
    Verifies that the BacktestEngine correctly respects input parameters.
    This ensures that the 'plumbing' from arguments to logic is working.
    """
    
    @pytest.fixture
    def mock_data(self):
        dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
        data = pd.DataFrame({
            "open": [100.0] * 10,
            "close": [100.0] * 10, # Flat price
            "high": [105.0] * 10,
            "low": [95.0] * 10,
            "volume": [1000] * 10
        }, index=dates)
        return data

    def test_commission_impact(self, mock_data):
        """
        Case A: Commission Impact
        Verify that higher commission leads to lower final equity.
        """
        signals = pd.Series([0.0] * 10, index=mock_data.index)
        signals.iloc[0] = 1.0 # Buy
        signals.iloc[5] = 0.0 # Sell
        
        # Run 1: Zero Commission
        engine_0 = BacktestEngine(initial_capital=10000, commission_rate=0.0, slippage=0.0)
        engine_0.run(mock_data, signals)
        res_0 = engine_0.current_capital
        
        # Run 2: High Commission (10%)
        engine_high = BacktestEngine(initial_capital=10000, commission_rate=0.1, slippage=0.0)
        engine_high.run(mock_data, signals)
        res_high = engine_high.current_capital
        
        assert res_high < res_0, f"High commission ({res_high}) should result in lower capital than zero commission ({res_0})"
        
        # Specific check: Buy 100 shares @ 100 = 10000. Comm 10% = 1000.
        # Sell 100 shares @ 100 = 10000. Comm 10% = 1000.
        # Total Loss = 2000. Final ~ 8000.
        # Zero comm final = 10000.
        assert res_high < 9000, "Should have lost significant money to commission"

    def test_slippage_impact(self, mock_data):
        """
        Case B: Slippage Impact
        Verify that higher slippage leads to lower final equity.
        """
        signals = pd.Series([0.0] * 10, index=mock_data.index)
        signals.iloc[0] = 1.0 # Buy
        signals.iloc[5] = 0.0 # Sell
        
        # Run 1: Zero Slippage
        engine_0 = BacktestEngine(initial_capital=10000, commission_rate=0.0, slippage=0.0)
        engine_0.run(mock_data, signals)
        res_0 = engine_0.current_capital
        
        # Run 2: High Slippage (5%)
        # Buy Price = 100 * 1.05 = 105
        # Sell Price = 100 * 0.95 = 95
        # Loss 10 per share.
        engine_high = BacktestEngine(initial_capital=10000, commission_rate=0.0, slippage=0.05)
        engine_high.run(mock_data, signals)
        res_high = engine_high.current_capital
        
        assert res_high < res_0, f"High slippage ({res_high}) should result in lower capital than zero slippage ({res_0})"
        assert res_high < 9500, "Should have lost money due to slippage"

    def test_initial_capital_impact(self, mock_data):
        """
        Case C: Initial Capital Impact
        Verify that starting capital is correctly set.
        """
        signals = pd.Series([0.0] * 10, index=mock_data.index)
        
        # Run 1: 1,000
        engine_1k = BacktestEngine(initial_capital=1000)
        engine_1k.run(mock_data, signals)
        assert engine_1k.initial_capital == 1000.0
        assert engine_1k.current_capital == 1000.0
        
        # Run 2: 100,000
        engine_100k = BacktestEngine(initial_capital=100000)
        engine_100k.run(mock_data, signals)
        assert engine_100k.initial_capital == 100000.0
        assert engine_100k.current_capital == 100000.0
