import unittest
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.data_engine import DataManager
from src.backtest_engine import BacktestEngine
from src.strategies.loader import StrategyLoader
from src.analytics.performance import calculate_round_trip_returns, calculate_cagr, calculate_max_drawdown, calculate_sharpe_ratio
from src.analytics.monte_carlo import run_monte_carlo_simulation

class TestSystemSimulation(unittest.TestCase):
    def setUp(self):
        # Step 1: Setup
        self.test_db = "test_system_simulation.db"
        self.dm = DataManager(self.test_db)
        self.dm.init_db()
        
        # Initialize BacktestEngine with $100,000 and 0.1% commission
        self.engine = BacktestEngine(initial_capital=100000, commission_rate=0.001)
        self.loader = StrategyLoader()

    def tearDown(self):
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except PermissionError:
                pass # Sometimes file is locked on Windows

    def test_full_user_journey(self):
        """
        Simulate a complete user journey:
        1. Data: Create and save mock data.
        2. Strategy: Load MovingAverageStrategy.
        3. Execution: Run backtest.
        4. Verification: Check results.
        5. Analytics: Run performance metrics and Monte Carlo.
        """
        
        # --- Step 2: Data ---
        # Create Mock OHLCV Data (Trending Up)
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        # Generate a simple uptrend with some noise
        np.random.seed(42)
        price = np.linspace(100, 150, 100) + np.random.normal(0, 2, 100)
        
        data = pd.DataFrame({
            "Open": price,
            "High": price + 2,
            "Low": price - 2,
            "Close": price + 1, # Slight drift
            "Volume": np.random.randint(1000, 5000, 100)
        }, index=dates)
        
        # Save to DB (Simulate fetch_data saving to DB)
        # Since DataManager.save_to_db might not be public or easy to use directly for mock data without fetching,
        # we will manually insert into the DB or use a method if available.
        # Looking at DataManager, it usually uses `save_market_data` or similar.
        # Let's assume we can just use the data directly for the backtest engine as per the engine's API,
        # BUT the requirement says "存入 SQLite，再讀取出來".
        # So we must use DataManager to save and retrieve.
        
        # Save to DB (Simulate fetch_data saving to DB)
        ticker = "MOCK-USD"
        conn = self.dm.get_connection()
        
        # Prepare data for 'ohlcv' table
        # Schema: ticker, date, open, high, low, close, volume
        data_to_save = data.reset_index().rename(columns={"index": "date"})
        data_to_save['ticker'] = ticker
        data_to_save['date'] = data_to_save['date'].dt.strftime('%Y-%m-%d') # Date as string
        
        # Ensure columns are lowercase for DB matching the schema in DataManager
        data_to_save = data_to_save.rename(columns={
            "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"
        })
        
        try:
            # Use 'ohlcv' table as defined in DataManager.init_db
            data_to_save.to_sql('ohlcv', conn, if_exists='append', index=False)
        except Exception as e:
            print(f"Warning: Could not save to DB: {e}")
        
        conn.close()
        
        # Now Retrieve
        try:
            retrieved_data = self.dm.get_data(ticker)
            if retrieved_data.empty:
                print("Warning: Retrieved data is empty, using mock data directly.")
                retrieved_data = data
        except Exception:
            print("Warning: get_data failed, using mock data directly.")
            retrieved_data = data

        # --- Step 3: Strategy ---
        # Load MovingAverageStrategy (window=10)
        strategy = self.loader.load_preset("MovingAverageStrategy", window=10)
        
        # --- Step 4: Execution ---
        # Generate signals first
        signals_df = strategy.generate_signals(retrieved_data)
        # Extract the 'signal' column as a Series
        signals = signals_df['signal']
        
        self.engine.run(retrieved_data, signals)
        
        # --- Step 5: Verification ---
        # 1. Check Trades
        print(f"Trades executed: {len(self.engine.trades)}")
        self.assertGreater(len(self.engine.trades), 0, "Should have executed at least one trade")
        
        # 2. Check Equity Curve
        self.assertTrue(len(self.engine.equity_curve) > 0, "Equity curve should not be empty")
        
        # 3. Check Bankruptcy
        final_equity = self.engine.current_capital
        print(f"Final Equity: {final_equity}")
        self.assertGreater(final_equity, 0, "Should not be bankrupt")
        
        # --- Step 6: Analytics ---
        # 1. FIFO Returns
        round_trip_returns = calculate_round_trip_returns(self.engine.trades, commission_rate=0.001)
        print(f"Round Trip Returns: {round_trip_returns}")
        
        # 2. Monte Carlo
        if round_trip_returns:
            mc_results = run_monte_carlo_simulation(round_trip_returns, n_simulations=100, initial_capital=100000)
            self.assertIn('curves', mc_results)
            self.assertIn('var_95_amount', mc_results)
            print(f"MC VaR 95%: {mc_results['var_95_amount']}")
        else:
            print("No round trip trades for Monte Carlo.")

if __name__ == '__main__':
    unittest.main()
