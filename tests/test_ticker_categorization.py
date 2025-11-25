import pytest
from src.utils import categorize_ticker

def test_categorize_ticker_crypto():
    assert categorize_ticker("BTC-USD") == "Crypto"
    assert categorize_ticker("ETH-USD") == "Crypto"
    assert categorize_ticker("btc-usd") == "Crypto"  # Case insensitivity

def test_categorize_ticker_tw():
    assert categorize_ticker("2330.TW") == "TW"
    assert categorize_ticker("0050.TW") == "TW"
    assert categorize_ticker("6547.TWO") == "TW"
    assert categorize_ticker("2330.tw") == "TW" # Case insensitivity

def test_categorize_ticker_us():
    assert categorize_ticker("AAPL") == "US"
    assert categorize_ticker("TSLA") == "US"
    assert categorize_ticker("MSFT") == "US"
    assert categorize_ticker("aapl") == "US" # Case insensitivity

def test_categorize_ticker_other():
    assert categorize_ticker("Unknown123") == "Other"
    assert categorize_ticker("^GSPC") == "Other"
    assert categorize_ticker("12345") == "Other"
