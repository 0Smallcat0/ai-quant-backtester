
import os
import unittest
import sqlite3
import shutil
from src.data_engine import DataManager

class TestHardReset(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_market_data.db"
        self.test_cache_dir = "test_sentiment_cache"
        
        # Setup DataManager with test paths
        self.dm = DataManager(db_path=self.test_db)
        # Mock news_engine with a dummy object that has cache_dir
        class DummyNewsEngine:
            def __init__(self, cache_dir):
                self.cache_dir = cache_dir
        self.dm.news_engine = DummyNewsEngine(self.test_cache_dir)
        
        # Create Dummy Data
        self.dm.init_db()
        if not os.path.exists(self.test_cache_dir):
            os.makedirs(self.test_cache_dir)
        with open(os.path.join(self.test_cache_dir, "test.parquet"), 'w') as f:
            f.write("dummy data")
            
    def test_hard_reset(self):
        # Verify existence before
        self.assertTrue(os.path.exists(self.test_db))
        self.assertTrue(os.path.exists(os.path.join(self.test_cache_dir, "test.parquet")))
        
        # Execute Reset
        self.dm.hard_reset()
        
        # Verify 1: DB file should be deleted (or re-created empty)
        # Hard reset deletes and then runs init_db, so file should exist but be empty/new.
        self.assertTrue(os.path.exists(self.test_db))
        
        # Check tables are empty but exist
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_names = [t[0] for t in tables]
        self.assertIn('ohlcv', table_names)
        self.assertIn('metadata', table_names)
        
        cursor.execute("SELECT count(*) FROM ohlcv")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 0)
        conn.close()
        
        # Verify 2: Cache file should be gone
        self.assertFalse(os.path.exists(os.path.join(self.test_cache_dir, "test.parquet")))
        # Directory should still exist
        self.assertTrue(os.path.exists(self.test_cache_dir))

    def tearDown(self):
        # Cleanup
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        if os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir)

if __name__ == '__main__':
    unittest.main()
