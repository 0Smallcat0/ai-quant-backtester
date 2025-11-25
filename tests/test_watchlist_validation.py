import unittest
import os
from src.data_engine import DataManager

class TestWatchlistValidation(unittest.TestCase):
    def setUp(self):
        # Use a temporary DB for testing
        self.test_db = "test_watchlist_validation.db"
        self.dm = DataManager(self.test_db)
        self.dm.init_db()

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_add_empty_ticker(self):
        """Case A: Test adding an empty ticker raises ValueError."""
        with self.assertRaises(ValueError):
            self.dm.add_to_watchlist("")
        
        # Verify nothing was added
        watchlist = self.dm.get_watchlist()
        self.assertEqual(len(watchlist), 0)

    def test_add_whitespace_ticker(self):
        """Case B: Test adding a whitespace-only ticker raises ValueError."""
        with self.assertRaises(ValueError):
            self.dm.add_to_watchlist("   ")
            
        # Verify nothing was added
        watchlist = self.dm.get_watchlist()
        self.assertEqual(len(watchlist), 0)

    def test_add_valid_ticker(self):
        """Case C: Test adding a valid ticker works."""
        self.dm.add_to_watchlist("AAPL")
        
        # Verify it was added
        watchlist = self.dm.get_watchlist()
        self.assertIn("AAPL", watchlist)
        self.assertEqual(len(watchlist), 1)

if __name__ == '__main__':
    unittest.main()
