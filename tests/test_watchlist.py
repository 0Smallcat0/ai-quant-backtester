import unittest
import sqlite3
import os
from src.data_engine import DataManager

class TestWatchlist(unittest.TestCase):
    def setUp(self):
        # Use a temporary DB for testing
        self.test_db = "test_watchlist.db"
        self.test_db = "test_watchlist.db"
        print(f"Setting up test with DB: {self.test_db}")
        print(f"DataManager class: {DataManager}")
        import inspect
        print(f"DataManager file: {inspect.getfile(DataManager)}")
        print(f"init_db source: {inspect.getsource(DataManager.init_db)}")
        self.dm = DataManager(self.test_db)
        self.dm.init_db()

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_add_symbol_to_watchlist(self):
        """Test adding a symbol to the watchlist."""
        self.dm.add_to_watchlist("AAPL")
        
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT symbol FROM tracked_symbols WHERE symbol='AAPL'")
        result = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "AAPL")

    def test_add_duplicate_symbol(self):
        """Test adding a duplicate symbol does not raise error."""
        self.dm.add_to_watchlist("AAPL")
        try:
            self.dm.add_to_watchlist("AAPL")
        except Exception as e:
            self.fail(f"Adding duplicate symbol raised exception: {e}")
            
        watchlist = self.dm.get_watchlist()
        self.assertEqual(len(watchlist), 1)

    def test_get_all_tracked_symbols(self):
        """Test retrieving all tracked symbols."""
        self.dm.add_to_watchlist("AAPL")
        self.dm.add_to_watchlist("NVDA")
        
        watchlist = self.dm.get_watchlist()
        self.assertIn("AAPL", watchlist)
        self.assertIn("NVDA", watchlist)
        self.assertEqual(len(watchlist), 2)

    def test_remove_symbol(self):
        """Test removing a symbol from the watchlist."""
        self.dm.add_to_watchlist("AAPL")
        self.dm.remove_from_watchlist("AAPL")
        
        watchlist = self.dm.get_watchlist()
        self.assertNotIn("AAPL", watchlist)

if __name__ == '__main__':
    unittest.main()
