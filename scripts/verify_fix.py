from src.data_engine import DataManager
from src.config.settings import settings
import pandas as pd
import logging

# Setup basic logging to see the DataManager output
logging.basicConfig(level=logging.INFO)

def verify_fix():
    print("Initializing DataManager...")
    dm = DataManager(str(settings.DB_PATH))
    
    ticker = "0056.TW"
    start_date = "2024-01-01"
    
    print(f"Fetching data for {ticker} from {start_date}...")
    # This calls fetch_data -> yfinance_provider.fetch_history
    # If the fix works, it should download data AND volume should be > 0
    dm.fetch_data(ticker, start_date=start_date)
    
    print("Checking database content...")
    df = dm.get_data(ticker)
    
    if df.empty:
        print("FAIL: No data found in DB.")
        return

    print(f"Data found: {len(df)} rows.")
    print(df.tail())
    
    # Verify Volume
    zero_vol_count = (df['volume'] == 0).sum()
    total_rows = len(df)
    zero_vol_ratio = zero_vol_count / total_rows
    
    print(f"Zero Volume Ratio: {zero_vol_ratio:.2%}")
    
    if zero_vol_ratio < 0.1: # Allow some legitimately 0 volume days if any, but 0056 shouldn't have many
        print("SUCCESS: Volume data is present and healthy.")
    else:
        print("FAIL: Too many zero volume days. Fix might not be working.")

if __name__ == "__main__":
    verify_fix()
