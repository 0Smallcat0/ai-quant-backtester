import pytest
from src.utils import detect_market

def test_categorize_ticker_crypto():
    # 'Crypto' title case was the old behavior. detect_market returns 'CRYPTO' (UC)
    assert detect_market("BTC-USD") == "CRYPTO"
    assert detect_market("ETH-USD") == "CRYPTO"
    assert detect_market("btc-usd") == "CRYPTO"  # Case insensitivity

def test_categorize_ticker_tw():
    assert detect_market("2330.TW") == "TW"
    assert detect_market("0050.TW") == "TW"
    assert detect_market("6547.TWO") == "TW"
    assert detect_market("2330.tw") == "TW" # Case insensitivity

def test_categorize_ticker_us():
    assert detect_market("AAPL") == "US"
    assert detect_market("TSLA") == "US"
    assert detect_market("MSFT") == "US"
    assert detect_market("aapl") == "US" # Case insensitivity

def test_categorize_ticker_other():
    assert detect_market("Unknown123") == "Other"
    assert detect_market("^GSPC") == "Other"
    assert detect_market("12345") == "Other"
