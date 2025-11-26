import pytest
from unittest.mock import MagicMock, patch
from src.data_engine import DataManager
from src.config.settings import settings

@pytest.fixture
def data_manager():
    return DataManager("test.db")

def test_config_usage_known_cryptos(data_manager):
    """
    Case A: Verify Config Usage (KNOWN_CRYPTOS)
    Check if normalize_ticker correctly identifies tickers in settings.KNOWN_CRYPTOS.
    We monkeypatch settings.KNOWN_CRYPTOS to ensure it's reading from settings.
    """
    # Test with a standard crypto from settings
    assert data_manager.normalize_ticker("BTC") == "BTC-USD"

    # Test with a NEW crypto added via monkeypatch to verify dynamic config usage
    with patch.object(settings, 'KNOWN_CRYPTOS', {'TESTCOIN'}):
        # Re-instantiate or just call method if it doesn't cache settings (it shouldn't)
        # Note: If DataManager caches settings on init, this might fail. 
        # But based on code, it accesses local var or global settings.
        # The current code has hardcoded set. We expect the refactored code to use settings.KNOWN_CRYPTOS.
        
        # If the code is NOT refactored yet, this test MIGHT fail or pass depending on implementation.
        # But we are writing the test FIRST (Red).
        # If the code is hardcoded, "TESTCOIN" won't be recognized.
        assert data_manager.normalize_ticker("TESTCOIN") == "TESTCOIN-USD"

def test_sanitization_usage(data_manager):
    """
    Case B: Verify Sanitization (sanitize_ticker)
    Call normalize_ticker with messy input and assert it returns clean ticker.
    This verifies sanitize_ticker is being called.
    """
    # " ' aApl ' " -> "AAPL" (US stock)
    assert data_manager.normalize_ticker("' aApl '") == "AAPL"
    
    # " ' btc ' " -> "BTC-USD" (Crypto)
    assert data_manager.normalize_ticker("' btc '") == "BTC-USD"
