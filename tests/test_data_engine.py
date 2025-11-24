import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_engine import DataManager
from config.settings import DB_PATH

class TestDataManager(unittest.TestCase):
    def setUp(self):
        self.dm = DataManager(str(DB_PATH))

    def test_ticker_normalization_tw(self):
        """Test normalization for Taiwan stocks"""
        # We need to mock yfinance to avoid actual network calls and ensure deterministic behavior
        with patch('yfinance.Ticker') as mock_ticker:
            # Setup mock to return a non-empty history for .TW
            mock_instance = MagicMock()
            mock_instance.history.return_value = "some_data" # Just needs to be truthy/non-empty
            mock_ticker.return_value = mock_instance
            
            result = self.dm.normalize_ticker("2330")
            self.assertEqual(result, "2330.TW")

    def test_ticker_normalization_crypto(self):
        """Test normalization for Crypto"""
        # Mocking isn't strictly necessary if logic is purely string-based for known list,
        # but if it checks yfinance, we should mock.
        # Based on my implementation:
        # 1. Checks if digit -> No
        # 2. Checks if in known_cryptos -> Yes ("BTC" is in set) -> returns "BTC-USD"
        result = self.dm.normalize_ticker("BTC")
        self.assertEqual(result, "BTC-USD")

    def test_ticker_normalization_us(self):
        """Test normalization for US stocks"""
        result = self.dm.normalize_ticker("NVDA")
        self.assertEqual(result, "NVDA")

    @patch('src.data_engine.yf.download')
    def test_download_progress_callback(self, mock_download):
        """Test that progress callback is called correctly"""
        # Setup mock to return a dummy DataFrame
        import pandas as pd
        mock_df = pd.DataFrame({
            'open': [100.0],
            'high': [105.0],
            'low': [95.0],
            'close': [100.0],
            'volume': [1000]
        }, index=pd.to_datetime(['2023-01-01']))
        mock_df.index.name = 'Date'
        mock_download.return_value = mock_df
        
        # Create a mock callback
        mock_callback = MagicMock()
        
        # Call fetch_data with a specific range (e.g., 2 years)
        # 2022 and 2023
        self.dm.fetch_data("AAPL", start_date="2022-01-01", end_date="2023-12-31", progress_callback=mock_callback)
        
        # Verify callback calls
        # Should be called for 2022 (0/2), 2023 (1/2), and completion (1.0)
        # Total calls >= 3
        self.assertGreaterEqual(mock_callback.call_count, 3)
        
        # Verify arguments of first call
        # args[0] is progress (float), args[1] is message (str)
        first_call_args = mock_callback.call_args_list[0]
        self.assertEqual(first_call_args[0][0], 0.0) 
        
        # Verify last call is 1.0
        last_call_args = mock_callback.call_args_list[-1]
        self.assertEqual(last_call_args[0][0], 1.0)

if __name__ == '__main__':
    unittest.main()
