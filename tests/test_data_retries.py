import pytest
from unittest.mock import patch, MagicMock
from src.data_loader.providers.yfinance_provider import YFinanceProvider
from src.config.settings import settings
import pandas as pd

class TestDataRetries:
    
    def test_settings_loaded(self):
        """
        Case A: Verify settings are loaded.
        """
        assert hasattr(settings, 'MAX_RETRIES')
        assert hasattr(settings, 'RETRY_BACKOFF_FACTOR')
        assert settings.MAX_RETRIES == 3
        assert settings.RETRY_BACKOFF_FACTOR == 2.0

    @patch('src.data_loader.providers.yfinance_provider.yf.download')
    @patch('src.data_loader.providers.yfinance_provider.time.sleep')
    def test_retry_logic(self, mock_sleep, mock_download):
        """
        Case B: Verify retry logic uses MAX_RETRIES and RETRY_BACKOFF_FACTOR.
        """
        # Setup mock to always fail
        mock_download.side_effect = Exception("Connection Error")
        
        provider = YFinanceProvider()
        
        # Expect exception after retries exhausted
        try:
            provider.fetch_history("AAPL", "2023-01-01", "2023-01-05")
        except Exception:
            pass
        
        # Verify call count matches MAX_RETRIES
        assert mock_download.call_count == settings.MAX_RETRIES
        
        # Verify sleep calls
        # Should sleep MAX_RETRIES - 1 times
        assert mock_sleep.call_count == settings.MAX_RETRIES - 1
        
    @patch('src.data_loader.providers.yfinance_provider.yf.download')
    @patch('src.data_loader.providers.yfinance_provider.time.sleep')
    def test_retry_logic_custom_settings(self, mock_sleep, mock_download):
        """
        Verify that changing settings actually changes behavior.
        """
        mock_download.side_effect = Exception("Fail")
        
        # Patch settings
        with patch.object(settings, 'MAX_RETRIES', 2), \
             patch.object(settings, 'RETRY_BACKOFF_FACTOR', 1.5):
            
            provider = YFinanceProvider()
            try:
                provider.fetch_history("AAPL", "2023-01-01", "2023-01-05")
            except Exception:
                pass
            
            # Should retry 2 times
            assert mock_download.call_count == 2
            
            # Should sleep 1 time (2-1)
            assert mock_sleep.call_count == 1
            
            # Sleep time should be 1.5 ** 0 = 1.0
            mock_sleep.assert_called_with(1.0)
