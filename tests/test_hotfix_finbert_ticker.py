
import pytest
from src.data_engine import DataManager
from src.config.settings import settings
import re

def test_normalize_ticker_us_stock():
    dm = DataManager(db_path=":memory:")
    
    # Standard US Stock which was problematic
    ticker = "NVDA"
    normalized = dm.normalize_ticker(ticker)
    
    # Expect NVDA (no suffix)
    assert normalized == "NVDA", f"Expected NVDA, got {normalized}"
    
    # Another example
    ticker = "AAPL"
    normalized = dm.normalize_ticker(ticker)
    assert normalized == "AAPL", f"Expected AAPL, got {normalized}"

def test_normalize_ticker_crypto():
    dm = DataManager(db_path=":memory:")
    
    # Known Crypto
    ticker = "BTC"
    normalized = dm.normalize_ticker(ticker)
    # Checks known list -> Adds suffix[0] -> BTC-USD
    assert normalized == "BTC-USD", f"Expected BTC-USD for known crypto, got {normalized}"
    
    # Unknown Crypto (Short) -> Should be treated as US Stock now due to hotfix
    ticker = "SHIB" # 4 letters, not in KNOWN_CRYPTOS
    normalized = dm.normalize_ticker(ticker)
    assert normalized == "SHIB", f"Expected SHIB (skipped crypto), got {normalized}"

if __name__ == "__main__":
    try:
        test_normalize_ticker_us_stock()
        print("test_normalize_ticker_us_stock PASSED")
        test_normalize_ticker_crypto()
        print("test_normalize_ticker_crypto PASSED")
    except AssertionError as e:
        print(f"FAILED: {e}")
        exit(1)
