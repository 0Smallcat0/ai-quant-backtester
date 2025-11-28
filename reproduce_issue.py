from src.data_engine import DataManager
import logging

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO)

def test_normalization():
    dm = DataManager(db_path=":memory:")
    ticker = "00679B"
    
    print(f"Testing normalization for: {ticker}")
    normalized = dm.normalize_ticker(ticker)
    print(f"Result: {normalized}")
    
    if normalized == ticker:
        print("FAIL: Ticker was not normalized (no suffix added).")
    else:
        print(f"SUCCESS: Ticker normalized to {normalized}")

if __name__ == "__main__":
    test_normalization()
