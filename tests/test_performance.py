import unittest
import sqlite3
import pandas as pd
import time
import os
import shutil
from unittest.mock import MagicMock, patch
from src.data_engine import DataManager
from src.config.settings import settings

class TestPerformance(unittest.TestCase):
    def setUp(self):
        # Use a temporary DB for testing
        self.test_db_path = "test_perf.db"
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        
        # Initialize DM
        self.dm = DataManager(db_path=self.test_db_path)
        self.dm.init_db()
        
        # Populate dummy data for Query Speed Test
        self._populate_dummy_data()

    def tearDown(self):
        if hasattr(self, 'dm'):
            self.dm.get_connection().close()
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except:
                pass

    def _populate_dummy_data(self):
        # Insert 10,000 rows for 'TEST_SYM'
        dates = pd.date_range(start="2000-01-01", periods=10000, freq='D')
        data = []
        for d in dates:
            data.append(('TEST_SYM', d.strftime('%Y-%m-%d'), 100.0, 105.0, 95.0, 100.0, 1000))
        
        conn = self.dm.get_connection()
        with conn:
            conn.executemany('INSERT INTO ohlcv VALUES (?,?,?,?,?,?,?)', data)
        conn.close()

    def test_case_1_query_speed(self):
        """Benchmark SQL Range Query vs Full Load"""
        # 1. Measure SQL Range Query (New Method)
        start_time = time.time()
        # Query last 100 days
        df_range = self.dm.get_data('TEST_SYM', start_date="2027-01-01", end_date="2027-05-01") 
        # Note: 10000 days from 2000 is approx 27 years -> 2027
        elapsed_range = time.time() - start_time
        
        print(f"\n[Benchmark] SQL Range Query Time: {elapsed_range:.6f}s")
        
        # 2. Measure Full Load (Old Method Simulation)
        start_time = time.time()
        # Simulate old behavior: query all, then filter
        # We can't strictly call old method efficiently without modifying code, 
        # but we can call get_data with None dates (which calls SQL with 1900-2099) 
        # which effectively scans the index but retrieves all rows.
        df_full = self.dm.get_data('TEST_SYM')
        # Then filter
        df_filtered = df_full[(df_full.index >= "2027-01-01") & (df_full.index <= "2027-05-01")]
        elapsed_full = time.time() - start_time
        
        print(f"[Benchmark] Full Load + Filter Time: {elapsed_full:.6f}s")
        
        # Assertion: Range query should be faster or comparable but loads much less data
        # Ideally range query is faster because of I/O reduction.
        self.assertLess(len(df_range), len(df_full))
        # Depending on machine, strict time assertion might be flaky, but let's try a soft one
        # or just ensure it works concurrently.
        # We at least assert data correctness
        self.assertEqual(len(df_range), len(df_filtered))

    @patch('src.data_engine.DataManager.update_data_if_needed')
    def test_case_2_parallel_fetch(self, mock_update):
        """Benchmark Parallel Fetching"""
        # Mock update to take 0.5s
        def side_effect(*args, **kwargs):
            time.sleep(0.5)
        mock_update.side_effect = side_effect
        
        # Add 5 fake symbols to watchlist
        conn = self.dm.get_connection()
        with conn:
            for i in range(5):
                conn.execute("INSERT INTO tracked_symbols (symbol) VALUES (?)", (f"SYM_{i}",))
        conn.close()
        
        start_time = time.time()
        self.dm.update_all_tracked_symbols()
        total_time = time.time() - start_time
        
        print(f"\n[Benchmark] Parallel Update Time (5 items * 0.5s task): {total_time:.4f}s")
        
        # If serial, it would take 2.5s+. If parallel (max_workers=5), approx 0.5-0.6s.
        # Allow some overhead, ensure it's < 1.5s
        self.assertLess(total_time, 1.5)
        self.assertEqual(mock_update.call_count, 5)

if __name__ == '__main__':
    unittest.main()
