import sys
import os
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config.settings import settings
from src.data_engine import DataManager
from src.backtest.thick_engine import apply_latching_engine

class MockBollingerStrategy:
    """
    Simulates the AI-Generated Mean Reversion Strategy.
    """
    def __init__(self, window=20, std_dev=2.0):
        self.window = window
        self.std_dev = std_dev

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df.columns = [c.lower() for c in df.columns]

        # Calculate Indicators
        df['ma'] = df['close'].rolling(window=self.window).mean()
        df['std'] = df['close'].rolling(window=self.window).std()
        df['upper'] = df['ma'] + (df['std'] * self.std_dev)
        df['lower'] = df['ma'] - (df['std'] * self.std_dev)
        
        # Define Signals (Thin Prompt Style)
        # Entry: Close < Lower Band (Mean Reversion Buy)
        # Using shift(1) to avoid lookahead bias if executing on Open, 
        # but typically signals are generated on Closed Candle T for T+1.
        # But for 'signals' generation, we usually just flag the condition on Day T.
        df['entries'] = df['close'] < df['lower']
        
        # Exit: Close > MA (Reversion to Mean Sell)
        df['exits'] = df['close'] > df['ma']
        
        return df

def run_diagnosis(ticker="0050.TW"):
    print(f"--- Diagnosing Ticker: {ticker} ---")
    
    # 1. Load Data
    # Setup DataManager
    if not os.path.exists(settings.DB_PATH):
        print(f"Database not found at {settings.DB_PATH}")
        # Try to use relative path if running from script
        db_path = os.path.join(settings.BASE_DIR, "data", "market_data.db")
        print(f"Trying {db_path}...")
        dm = DataManager(db_path)
    else:
        dm = DataManager(settings.DB_PATH)

    # Check if we have data, if not try to fetch (or warning)
    try:
        df = dm.get_data(ticker)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    if df.empty:
        print(f"Data empty for {ticker}. Trying fallback ticker BTC-USD...")
        try:
             df = dm.get_data("BTC-USD")
        except:
             print("Could not fetch BTC-USD either.")
             return
        if df.empty:
             print("No data found.")
             # Create Mock Data for verification
             print("Creating Mock Data...")
             dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
             df = pd.DataFrame(index=dates)
             t = np.arange(len(dates))
             # Sine wave for mean reversion
             df['close'] = 100 + 10 * np.sin(t * 0.1) + np.random.normal(0, 2, len(dates))
             df['open'] = df['close']
             df['high'] = df['close'] + 1
             df['low'] = df['close'] - 1
             df['volume'] = 1000

    # Filter last 2 years (or full if short)
    df = df.sort_index()
    if len(df) > 500:
        df = df.iloc[-500:]

    print(f"Data Range: {df.index[0].date()} to {df.index[-1].date()} ({len(df)} rows)")

    # 2. Run Strategy
    strategy = MockBollingerStrategy()
    signals_df = strategy.generate_signals(df)

    # 3. Apply Latching
    print("Applying Thick Engine Latching...")
    signals_df['position_state'] = apply_latching_engine(signals_df['entries'], signals_df['exits'])
    
    # 4. Statistics
    total_days = len(signals_df)
    entry_count = signals_df['entries'].sum()
    exit_count = signals_df['exits'].sum()
    holding_days = signals_df['position_state'].sum()
    
    avg_exposure = holding_days / total_days if total_days > 0 else 0
    
    # Calculate Average Holding Period
    # Count consecutive True blocks
    state_int = signals_df['position_state'].astype(int)
    state_change = state_int.diff()
    # clean first NaN
    state_change.iloc[0] = state_int.iloc[0] # If starts with 1, it's a start
    
    # +1 means start of trade
    trade_starts = (state_change == 1).sum()
    
    avg_holding_period = holding_days / trade_starts if trade_starts > 0 else 0

    print("\n--- Diagnostic Results ---")
    print(f"Total Days Analyzed: {total_days}")
    print(f"Entry Signals (Triggers): {entry_count}")
    print(f"Exit  Signals (Triggers): {exit_count}")
    print(f"Trade Count (Latched):    {trade_starts}")
    print(f"Total Holding Days:       {holding_days}")
    print(f"Avg Holding Period:       {avg_holding_period:.2f} days")
    print(f"Avg Exposure (% Time):    {avg_exposure:.2%}")
    
    print("\n--- Sample Log (First 20 valid entries) ---")
    # Show rows where Entry is True and subsequent behavior
    entry_indices = signals_df.index[signals_df['entries']]
    
    if len(entry_indices) > 0:
        first_entry = entry_indices[0]
        # Get slice starting from first entry
        start_loc = signals_df.index.get_loc(first_entry)
        end_loc = min(start_loc + 20, len(signals_df))
        
        subset = signals_df.iloc[start_loc:end_loc]
        # print nicer
        print(subset[['close', 'lower', 'entries', 'ma', 'exits', 'position_state']].to_string())
    else:
        print("No entries found.")

if __name__ == "__main__":
    run_diagnosis()
