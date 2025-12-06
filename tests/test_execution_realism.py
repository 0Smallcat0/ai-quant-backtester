import pytest
import pandas as pd
from src.backtest_engine import BacktestEngine
from src.config.settings import settings

class TestExecutionRealism:
    def test_slippage_impact(self):
        """
        Case A: Slippage Impact
        Verify that slippage reduces PnL compared to a zero-slippage baseline.
        """
        # Data: Flat price to isolate slippage effect
        dates = pd.date_range(start="2023-01-01", periods=5, freq="D")
        data = pd.DataFrame({
            "open": [100.0] * 5,
            "close": [100.0] * 5,
            "high": [105.0] * 5,
            "low": [95.0] * 5,
            "volume": [1000] * 5
        }, index=dates)
        
        # Signal: Buy on Day 1, Sell on Day 3
        signals = pd.Series([0.0] * 5, index=dates)
        signals.iloc[0] = 1.0  # Buy
        signals.iloc[2] = 0.0  # Sell (Flat)
        
        # 1. Baseline: No Slippage
        engine_base = BacktestEngine(initial_capital=10000, commission_rate=0.0, slippage=0.0, min_commission=0.0)
        engine_base.run(data, signals)
        pnl_base = engine_base.current_capital - engine_base.initial_capital
        
        # 2. With Slippage: 0.1%
        # Buy at 100 * 1.001 = 100.1
        # Sell at 100 * 0.999 = 99.9
        # Loss per share = 0.2
        engine_slip = BacktestEngine(initial_capital=10000, commission_rate=0.0, slippage=0.001, min_commission=0.0)
        engine_slip.run(data, signals)
        pnl_slip = engine_slip.current_capital - engine_slip.initial_capital
        
        # Assertions
        assert pnl_base == 0.0, "Baseline should have 0 PnL with flat prices and no costs"
        assert pnl_slip < pnl_base, "Slippage should reduce PnL"
        
        # Verify exact execution prices in trades
        trades = engine_slip.trades
        assert len(trades) >= 2
        buy_trade = trades[0]
        sell_trade = trades[1]
        
        assert buy_trade.type == "BUY"
        assert buy_trade.entry_price == pytest.approx(100.1)
        
        assert sell_trade.type == "SELL"
        assert sell_trade.entry_price == pytest.approx(99.9)

    def test_strict_cash_limit(self):
        """
        Case B: Strict Cash Limit
        Verify that the engine strictly enforces cash limits using floor calculation,
        preventing negative cash balances even by a fraction.
        """
        dates = pd.date_range(start="2023-01-01", periods=3, freq="D")
        # Price 100
        data = pd.DataFrame({
            "open": [100.0] * 3,
            "close": [100.0] * 3,
            "high": [100.0] * 3,
            "low": [100.0] * 3,
            "volume": [1000] * 3
        }, index=dates)
        
        # Cash: 10,000
        # Target Buy: 101 shares -> Cost 10,100 (Exceeds cash)
        # Expected: Cap at 100 shares
        
        initial_capital = 10000.0
        engine = BacktestEngine(initial_capital=initial_capital, commission_rate=0.0, slippage=0.0, min_commission=0.0)
        
        # Force a signal that demands more than we have
        # We need to manually construct a signal that asks for > 100% equity if we rely on fixed_percent=1.0
        # Or we can use fixed_amount. Let's use fixed_amount for clarity or just rely on the engine's internal check logic.
        # The engine uses `target_exposure = current_equity * target * signal`.
        # If we set signal=2.0 (200% leverage), it should try to buy 200 shares.
        
        signals = pd.Series([0.0] * 3, index=dates)
        signals.iloc[0] = 2.0 # Try to buy 200%
        
        engine.run(data, signals)
        
        buy_trade = engine.trades[0]
        
        # Assertions
        assert buy_trade.quantity == 100.0, f"Should buy exactly 100 shares, got {buy_trade.quantity}"
        assert engine.current_capital >= 0.0, "Cash should not be negative"
        
        # Verify it didn't buy 100.99 or something if we didn't have floor (though quantity is usually float, 
        # the user asked for floor calculation which implies integer-like steps or at least strictly <= cash)
        # With price 100 and cash 10000, max is exactly 100. 
        # Let's try a case where division results in fraction.
        # Price 99, Cash 100. Max shares = floor(1.0101...) = 1.
        
        # Sub-test: Fractional capability check
        engine2 = BacktestEngine(initial_capital=100.0, commission_rate=0.0, slippage=0.0, min_commission=0.0)
        data2 = data.copy()
        data2['open'] = 99.0 # Price 99
        
        signals2 = pd.Series([0.0] * 3, index=dates)
        signals2.iloc[0] = 2.0 # Try to buy max
        
        engine2.run(data2, signals2)
        trade2 = engine2.trades[0]
        
        # 100 / 99 = 1.0101...
        # If floor is used, should be 1.0
        # If not, might be 1.0101...
        assert trade2.quantity == 1.0, f"Should floor quantity to 1.0, got {trade2.quantity}"
        assert engine2.current_capital >= 1.0, "Should have remainder cash"
