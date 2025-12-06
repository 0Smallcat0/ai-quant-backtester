import unittest
import pandas as pd
from src.backtest_engine import Trade
from src.analytics.performance import calculate_round_trip_returns

class TestPortfolioWeightedReturns(unittest.TestCase):
    def test_partial_allocation_return(self):
        """
        Test Case 1: Partial Allocation (1% of capital)
        Initial Capital: 10,000
        Buy 1 share at 100 (Cost 100, 1% allocation)
        Sell 1 share at 110 (Profit 10)
        
        Trade Return: (110 - 100) / 100 = 10%
        Portfolio Return: 10 / 10,000 = 0.1% (0.001)
        """
        trades = [
            Trade(
                entry_date=pd.Timestamp("2023-01-01"),
                entry_price=100.0,
                quantity=1,
                type="BUY",
                entry_equity=10000.0
            ),
            Trade(
                entry_date=pd.Timestamp("2023-01-02"),
                entry_price=110.0,
                quantity=1,
                type="SELL",
                entry_equity=10010.0 # Irrelevant for SELL side in calculation, but good for completeness
            )
        ]
        
        returns = calculate_round_trip_returns(trades)
        self.assertEqual(len(returns), 1)
        self.assertAlmostEqual(returns[0], 0.001, places=5)

    def test_full_allocation_return(self):
        """
        Test Case 2: Full Allocation (100% of capital)
        Initial Capital: 10,000
        Buy 100 shares at 100 (Cost 10,000, 100% allocation)
        Sell 100 shares at 110 (Profit 1,000)
        
        Trade Return: (110 - 100) / 100 = 10%
        Portfolio Return: 1,000 / 10,000 = 10% (0.10)
        """
        trades = [
            Trade(
                entry_date=pd.Timestamp("2023-01-01"),
                entry_price=100.0,
                quantity=100,
                type="BUY",
                entry_equity=10000.0
            ),
            Trade(
                entry_date=pd.Timestamp("2023-01-02"),
                entry_price=110.0,
                quantity=100,
                type="SELL",
                entry_equity=11000.0
            )
        ]
        
        returns = calculate_round_trip_returns(trades)
        self.assertEqual(len(returns), 1)
        self.assertAlmostEqual(returns[0], 0.10, places=5)

    def test_legacy_compatibility(self):
        """
        Test Case 3: Legacy Trade objects (no entry_equity)
        Should fallback to Trade Return
        """
        trades = [
            Trade(
                entry_date=pd.Timestamp("2023-01-01"),
                entry_price=100.0,
                quantity=1,
                type="BUY"
                # entry_equity missing (defaults to 0.0 via getattr)
            ),
            Trade(
                entry_date=pd.Timestamp("2023-01-02"),
                entry_price=110.0,
                quantity=1,
                type="SELL"
            )
        ]
        
        returns = calculate_round_trip_returns(trades)
        self.assertEqual(len(returns), 1)
        # Fallback to Trade Return: (110 - 100) / 100 = 0.10
        self.assertAlmostEqual(returns[0], 0.10, places=5)

if __name__ == '__main__':
    unittest.main()
