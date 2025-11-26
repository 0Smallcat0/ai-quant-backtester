import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.data_engine import DataManager
from src.config.settings import settings

@pytest.fixture
def data_manager():
    dm = DataManager(db_path=":memory:")
    dm.init_db()
    return dm

def test_ticker_normalization_tw(data_manager):
    """Test normalization for Taiwan stocks"""
    with patch('yfinance.Ticker') as mock_ticker:
        # Setup mock to return a non-empty history for .TW
        mock_instance = MagicMock()
        mock_instance.history.return_value = pd.DataFrame({"Close": [100]})
        mock_ticker.return_value = mock_instance
        
        # Mock settings.TICKER_SUFFIXES if needed, but using default is fine
        # Assuming settings.TICKER_SUFFIXES = ['.TW', '.TWO']
        
        result = data_manager.normalize_ticker("2330")
        assert result == "2330.TW"

def test_ticker_normalization_crypto(data_manager):
    """Test normalization for Crypto"""
    # Assuming BTC is in settings.KNOWN_CRYPTOS
    result = data_manager.normalize_ticker("BTC")
    assert result == "BTC-USD"

def test_ticker_normalization_us(data_manager):
    """Test normalization for US stocks"""
    result = data_manager.normalize_ticker("NVDA")
    assert result == "NVDA"

@patch('src.data_engine.yf.download')
@patch('src.data_engine.time.sleep')
def test_rate_limiting(mock_sleep, mock_download, data_manager):
    """Test that rate limiting sleep is called"""
    # Mock watchlist
    with patch.object(data_manager, 'get_watchlist', return_value=['AAPL', 'MSFT']):
        # Mock fetch_data to do nothing
        with patch.object(data_manager, 'fetch_data'):
            # Mock _calc_smart_start to avoid DB calls
            with patch.object(data_manager, '_calc_smart_start', return_value="2023-01-01"):
                data_manager.update_all_tracked_symbols()
                
                # Should sleep RATE_LIMIT_SLEEP * number of symbols
                assert mock_sleep.call_count == 2
                mock_sleep.assert_called_with(settings.RATE_LIMIT_SLEEP)
