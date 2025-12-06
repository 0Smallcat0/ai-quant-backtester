from src.data_engine import DataManager
from src.config.settings import settings
import logging
import pandas as pd

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_0050_final():
    dm = DataManager(str(settings.DB_PATH))
    ticker = "0050.TW"
    
    # 1. Purge
    print(f"=== Step 1: Purging {ticker} ===")
    dm.purge_ticker_data(ticker)
    
    # 2. Fetch (Targeted Range for Speed)
    print(f"=== Step 2: Fetching {ticker} (Recent Data Only) ===")
    dm.fetch_data(ticker, start_date="2024-01-01")
    
    # 3. Verify
    print(f"=== Step 3: Verifying {ticker} in DB ===")
    df = dm.get_data(ticker)
    
    if df.empty:
        print("FAIL: No data in DB.")
        return

    # Check Volume
    zero_rows = df[df['volume'] == 0]
    zero_vol_count = len(zero_rows)
    total = len(df)
    ratio = zero_vol_count / total
    
    print(f"Total Rows: {total}")
    print(f"Zero Volume Ratio: {ratio:.2%}")
    if zero_vol_count > 0:
        print("Zero Volume Dates:", zero_rows.index.strftime('%Y-%m-%d').tolist())
    
    print("Tail:\n", df.tail())
    
    # Strict check: 0050 should basically NEVER have 0 volume.
    if ratio < 0.05: # Allow small margin for error
        print("SUCCESS: 0050.TW fixed. Volume is healthy.")
    else:
        print("FAIL: Still too many zero volumes.")

if __name__ == "__main__":
    fix_0050_final()
