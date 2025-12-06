import pytest
from unittest.mock import MagicMock, patch
from src.data_engine import DataManager
from src.config.settings import settings

@pytest.fixture
def data_manager():
    return DataManager("test.db")

def test_config_usage_known_cryptos(data_manager):
    """
    Case A: Verify Config Usage (MARKET_CONFIG)
    Check if normalize_ticker correctly identifies tickers in settings.MARKET_CONFIG['CRYPTO']['known'].
    We monkeypatch settings.MARKET_CONFIG to ensure it's reading from settings.
    """
    # Test with a standard crypto from settings
    print(f"DEBUG: MARKET_CONFIG = {settings.MARKET_CONFIG}")
    assert data_manager.normalize_ticker("BTC") == "BTC-USD"

    # Test with a NEW crypto added via monkeypatch to verify dynamic config usage
    # We need to construct a mock MARKET_CONFIG
    mock_config = settings.MARKET_CONFIG.copy()
    mock_config['CRYPTO'] = mock_config['CRYPTO'].copy()
    mock_config['CRYPTO']['known'] = mock_config['CRYPTO']['known'].copy()
    mock_config['CRYPTO']['known'].add('TESTCOIN')
    
    with patch.object(settings, 'MARKET_CONFIG', mock_config):
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
