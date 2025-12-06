import yfinance as yf
import pandas as pd

def test_download(ticker, use_auto_adjust):
    print(f"Testing {ticker} with auto_adjust={use_auto_adjust}")
    df = yf.download(ticker, start="2023-01-01", end="2023-01-10", progress=False, multi_level_index=False, auto_adjust=use_auto_adjust)
    if 'Volume' in df.columns:
        zero_vol_count = (df['Volume'] == 0).sum()
        total = len(df)
        print(f"  Total rows: {total}, Zero Volume rows: {zero_vol_count}")
        if total > 0:
            print(f"  Zero Volume Ratio: {zero_vol_count/total:.2%}")
        print("  Head:\n", df.head())
    else:
        print("  No Volume column found!")

if __name__ == "__main__":
    test_download("0050.TW", True)   # Expected bad
    test_download("0050.TW", False)  # Expected good
