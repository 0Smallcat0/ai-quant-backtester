import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_engine import DataManager
from src.config.settings import settings

class TestDataManagerDateRange(unittest.TestCase):
    def setUp(self):
        self.dm = DataManager(str(settings.DB_PATH))

    @patch('src.data_engine.DataManager.fetch_data')
    @patch('src.data_engine.DataManager.get_watchlist')
    def test_update_all_tracked_symbols_with_dates(self, mock_get_watchlist, mock_fetch_data):
        """Test update_all_tracked_symbols with explicit start and end dates"""
        # Setup
        mock_get_watchlist.return_value = ["AAPL", "GOOGL"]
        start_date = "2020-01-01"
        end_date = "2023-01-01"
        
        # Execute
        self.dm.update_all_tracked_symbols(start_date=start_date, end_date=end_date)
        
        # Verify
        self.assertEqual(mock_fetch_data.call_count, 2)
        
        # Check calls
        mock_fetch_data.assert_any_call("AAPL", start_date=start_date, end_date=end_date, progress_callback=None)
        mock_fetch_data.assert_any_call("GOOGL", start_date=start_date, end_date=end_date, progress_callback=None)

    @patch('src.data_engine.DataManager.fetch_data')
    @patch('src.data_engine.DataManager.get_watchlist')
    def test_update_all_tracked_symbols_no_dates(self, mock_get_watchlist, mock_fetch_data):
        """Test update_all_tracked_symbols without explicit dates (smart logic)"""
        # Setup
        mock_get_watchlist.return_value = ["AAPL"]
        
        # Mock metadata to simulate no existing data
        with patch('src.data_engine.DataManager.get_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = None # No metadata
            
            # Execute
            self.dm.update_all_tracked_symbols()
            
            # Verify
            # Should default to 2000-01-01 start date and None end date (or implicit today)
            # Note: The implementation passes end_date=None if not provided
            mock_fetch_data.assert_called_with("AAPL", start_date="2000-01-01", end_date=None, progress_callback=None)

if __name__ == '__main__':
    unittest.main()
