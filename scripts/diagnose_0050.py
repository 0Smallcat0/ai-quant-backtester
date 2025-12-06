import yfinance as yf
import pandas as pd

def diagnose_0050():
    print("Fetching 0050.TW from YFinance (auto_adjust=False)...")
    # Fetch recent data to see current behavior
    df = yf.download("0050.TW", start="2024-01-01", progress=False, auto_adjust=False)
    
    if df.empty:
        print("No data fetched.")
        return

    if 'Volume' in df.columns:
        vol = df['Volume']
        print(f"Volume Head:\n{vol.head()}")
        print(f"Has NaN: {vol.isna().any()}")
        print(f"Has Zero: {(vol == 0).any()}")
        
        nan_count = vol.isna().sum()
        zero_count = (vol == 0).sum()
        total = len(vol)
        
        print(f"Total Rows: {total}")
        if isinstance(nan_count, pd.Series):
            nan_count = nan_count.iloc[0]
        if isinstance(zero_count, pd.Series):
            zero_count = zero_count.iloc[0]

        print(f"NaN Count: {nan_count} ({nan_count/total:.2%})")
        print(f"Zero Count: {zero_count} ({zero_count/total:.2%})")
    else:
        print("Volume column missing.")

if __name__ == "__main__":
    diagnose_0050()
