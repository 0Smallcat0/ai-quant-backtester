
import pytest
from src.utils import detect_market

def test_detect_market_tw():
    assert detect_market("2330.TW") == "TW"
    assert detect_market("0050.TW") == "TW"
    assert detect_market("00679B.TWO") == "TW"

def test_detect_market_us():
    assert detect_market("NVDA") == "US"
    assert detect_market("AAPL") == "US"
    assert detect_market("TSLA") == "US"

def test_detect_market_crypto():
    assert detect_market("BTC-USD") == "CRYPTO"
    assert detect_market("ETH-USD") == "CRYPTO"
    
    # Test known crypto without suffix if in config
    # settings.MARKET_CONFIG['CRYPTO']['known'] = {'BTC', 'ETH', ...}
    # Assuming config is loaded
    assert detect_market("BTC") == "CRYPTO" 
    assert detect_market("DOGE") == "CRYPTO"

def test_detect_market_other():
    assert detect_market("123") == "Other"
    assert detect_market("") == "Other"


