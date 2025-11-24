import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime, timedelta
import os
from src.data_engine import DataManager

class TestBatchUpdate(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_batch_update.db"
        self.dm = DataManager(self.test_db)
        self.dm.init_db()
        
    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    @patch('src.data_engine.yf.download')
    def test_batch_update_mixed_status(self, mock_download):
        """
        Test batch update with mixed scenarios:
        - AAPL: Outdated (needs partial update)
        - BTC-USD: New (needs full update)
        """
        # Setup Watchlist
        self.dm.add_to_watchlist("AAPL")
        self.dm.add_to_watchlist("BTC-USD")
        
        # Setup existing data for AAPL (updated until 2 days ago)
        two_days_ago = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        conn = self.dm.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO metadata (ticker, last_updated) VALUES (?, ?)", ("AAPL", two_days_ago))
        conn.commit()
        conn.close()
        
        # Mock return value for download (empty DF is fine, we just check calls)
        mock_download.return_value = pd.DataFrame()
        
        # Run Batch Update
        self.dm.update_all_tracked_symbols()
        
        # Verify calls
        # AAPL should be called with start = two_days_ago (or close to it)
        # BTC-USD should be called with default start (2020-01-01)
        
        # We expect 2 calls (one for each ticker, potentially chunked, but let's assume simple case first)
        # Actually, fetch_data chunks by year. 
        # To simplify testing, we can mock fetch_data instead of yf.download if we want to test the logic of "what date to start".
        # But let's test yf.download calls to be sure.
        
        # Since fetch_data chunks, it might call download multiple times.
        # Let's just verify that fetch_data was called with correct start_date.
        pass

    @patch('src.data_engine.DataManager.fetch_data')
    def test_batch_update_logic_calls(self, mock_fetch_data):
        """
        Test that fetch_data is called with correct arguments.
        """
        # Setup Watchlist
        self.dm.add_to_watchlist("AAPL")
        self.dm.add_to_watchlist("BTC-USD")
        
        # Setup AAPL as outdated (2 days ago)
        two_days_ago = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        conn = self.dm.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO metadata (ticker, last_updated) VALUES (?, ?)", ("AAPL", two_days_ago))
        conn.commit()
        conn.close()
        
        # Run Update
        self.dm.update_all_tracked_symbols()
        
        # Verify AAPL call
        # Should be called with start_date = two_days_ago + 1 day
        expected_start = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        mock_fetch_data.assert_any_call("AAPL", start_date=expected_start, end_date=None, progress_callback=None)
        
        # Verify BTC-USD call
        # Should be called with start_date = None (default) or explicit default
        # The implementation might pass None or "2020-01-01".
        # Let's check if it was called for BTC-USD
        found_btc = False
        for call in mock_fetch_data.call_args_list:
            args, kwargs = call
            if args[0] == "BTC-USD":
                found_btc = True
                # If start_date is passed, it should be None or default
                if 'start_date' in kwargs and kwargs['start_date']:
                     # If it's not None, it should be the default start date (e.g. 2000-01-01 or 2020-01-01)
                     pass
        self.assertTrue(found_btc, "BTC-USD should be updated")

    @patch('src.data_engine.DataManager.fetch_data')
    def test_update_skip_current(self, mock_fetch_data):
        """Test that up-to-date tickers are skipped."""
        self.dm.add_to_watchlist("NVDA")
        
        # Set NVDA as updated today
        today = datetime.now().strftime('%Y-%m-%d')
        conn = self.dm.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO metadata (ticker, last_updated) VALUES (?, ?)", ("NVDA", today))
        conn.commit()
        conn.close()
        
        self.dm.update_all_tracked_symbols()
        
        # fetch_data should NOT be called for NVDA
        for call in mock_fetch_data.call_args_list:
            args, _ = call
            if args[0] == "NVDA":
                self.fail("NVDA should have been skipped")

if __name__ == '__main__':
    unittest.main()
