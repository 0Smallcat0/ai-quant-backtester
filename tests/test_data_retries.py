import pytest
from unittest.mock import patch, MagicMock
from src.data_engine import DataManager
from src.config.settings import settings
import pandas as pd

class TestDataRetries:
    
    def test_settings_loaded(self):
        """
        Case A: Verify DataEngine reads new settings.
        We check if settings object has the new attributes.
        """
        assert hasattr(settings, 'MAX_RETRIES')
        assert hasattr(settings, 'RETRY_BACKOFF_FACTOR')
        assert settings.MAX_RETRIES == 3
        assert settings.RETRY_BACKOFF_FACTOR == 2.0

    @patch('src.data_engine.yf.download')
    @patch('src.data_engine.time.sleep')
    def test_retry_logic(self, mock_sleep, mock_download):
        """
        Case B: Verify retry logic uses MAX_RETRIES and RETRY_BACKOFF_FACTOR.
        """
        # Setup mock to always fail
        mock_download.side_effect = Exception("Connection Error")
        
        dm = DataManager(db_path=":memory:")
        
        # We need to verify that fetch_data uses the settings
        # Since fetch_data is complex and calls yf.download inside a loop, 
        # we'll test a single chunk download scenario.
        
        # Use a short date range to trigger only one chunk loop
        dm.fetch_data("AAPL", start_date="2023-01-01", end_date="2023-01-05")
        
        # Verify call count matches MAX_RETRIES
        assert mock_download.call_count == settings.MAX_RETRIES
        
        # Verify sleep calls
        # Should sleep MAX_RETRIES - 1 times
        # Sleep times should be: 2^0, 2^1, ...
        assert mock_sleep.call_count == settings.MAX_RETRIES - 1
        
        # Check backoff factor usage
        # We can't easily check the exact argument if we don't mock settings, 
        # but we can check if the logic follows the pattern.
        # Let's verify with a custom backoff factor to be sure it's not hardcoded.
        
    @patch('src.data_engine.yf.download')
    @patch('src.data_engine.time.sleep')
    def test_retry_logic_custom_settings(self, mock_sleep, mock_download):
        """
        Verify that changing settings actually changes behavior.
        """
        mock_download.side_effect = Exception("Fail")
        
        # Patch settings
        with patch.object(settings, 'MAX_RETRIES', 2), \
             patch.object(settings, 'RETRY_BACKOFF_FACTOR', 1.5):
            
            dm = DataManager(db_path=":memory:")
            dm.fetch_data("AAPL", start_date="2023-01-01", end_date="2023-01-05")
            
            # Should retry 2 times
            assert mock_download.call_count == 2
            
            # Should sleep 1 time (2-1)
            assert mock_sleep.call_count == 1
            
            # Sleep time should be 1.5 ** 0 = 1.0
            mock_sleep.assert_called_with(1.0)
