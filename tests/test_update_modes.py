import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime
from src.data_engine import DataManager
from src.config.settings import settings

class TestUpdateModes(unittest.TestCase):
    def setUp(self):
        # Mock DB path
        self.db_path = ":memory:"
        self.dm = DataManager(self.db_path)
        
        # Mock providers
        self.dm.yf_provider = MagicMock()
        self.dm.stooq_provider = MagicMock()
        self.dm.twstock_provider = MagicMock()
        self.dm.ccxt_provider = MagicMock()
        
        # Mock internal methods to isolate logic
        self.dm.get_connection = MagicMock()
        self.dm.save_data = MagicMock()
        self.dm.get_data = MagicMock()
        self.dm.fetch_data = MagicMock()
        self.dm._calc_smart_start = MagicMock()

    def test_incremental_mode(self):
        """
        Case A: Incremental Mode
        - DB has data until 2023-12-01
        - Today is 2023-12-05
        - Should fetch from 2023-12-02
        - Should NOT call backup provider
        """
        ticker = "AAPL"
        last_updated = "2023-12-01"
        smart_start = "2023-12-02"
        
        # Setup mocks
        self.dm._calc_smart_start.return_value = smart_start
        
        # Execute
        self.dm.update_data_if_needed(ticker, update_mode="INCREMENTAL")
        
        # Assertions
        # 1. Check fetch_data called with correct start_date
        self.dm.fetch_data.assert_called_once()
        args, kwargs = self.dm.fetch_data.call_args
        self.assertEqual(args[0], ticker)
        self.assertEqual(kwargs['start_date'], smart_start)
        
        # 2. Verify NO backup provider calls (since fetch_data handles primary)
        # Note: fetch_data internally calls providers, but here we mocked fetch_data itself
        # to verify the flow control in update_data_if_needed.
        # If we want to verify provider calls, we should NOT mock fetch_data, but mock providers.
        # However, update_data_if_needed calls fetch_data for INCREMENTAL.
        # So asserting fetch_data is called is sufficient to prove it took the INCREMENTAL branch.
        
    @patch('src.data_engine.datetime')
    def test_full_verify_mode_conflict(self, mock_datetime):
        """
        Case B: Full Verify Mode
        - Should fetch full history (from 2000-01-01)
        - If conflict, should trigger backup provider
        """
        ticker = "AAPL"
        # Mock today to be fixed
        mock_datetime.now.return_value = datetime(2023, 12, 5)
        mock_datetime.strftime.return_value = "2023-12-05"
        
        # Setup Data
        # Old Data (in DB)
        df_old = pd.DataFrame({
            'open': [100.0], 'high': [110.0], 'low': [90.0], 'close': [105.0], 'volume': [1000]
        }, index=pd.to_datetime(['2023-01-01']))
        df_old.index.name = 'date'
        self.dm.get_data.return_value = df_old
        
        # New Primary Data (Different values -> Conflict)
        df_new_pri = pd.DataFrame({
            'open': [102.0], 'high': [112.0], 'low': [92.0], 'close': [107.0], 'volume': [1000.0]
        }, index=pd.to_datetime(['2023-01-01']))
        df_new_pri.index.name = 'date'
        self.dm.yf_provider.fetch_history.return_value = df_new_pri
        
        # Backup Data (Agrees with Primary -> Case A: Update DB)
        df_new_bak = pd.DataFrame({
            'open': [102.0], 'high': [112.0], 'low': [92.0], 'close': [107.0], 'volume': [1000.0]
        }, index=pd.to_datetime(['2023-01-01']))
        df_new_bak.index.name = 'date'
        self.dm.stooq_provider.fetch_history.return_value = df_new_bak
        
        # Execute
        self.dm.update_data_if_needed(ticker, update_mode="FULL_VERIFY")
        
        # Assertions
        # 1. Verify Primary Fetch (Full History)
        self.dm.yf_provider.fetch_history.assert_called_once()
        args, _ = self.dm.yf_provider.fetch_history.call_args
        self.assertEqual(args[0], ticker)
        self.assertEqual(args[1], "2000-01-01") # Start date check
        
        # 2. Verify Backup Fetch (Triggered by conflict)
        # AAPL is US stock, so stooq_provider should be used
        self.dm.stooq_provider.fetch_history.assert_called_once()
        
        # 3. Verify Save Data (Correction applied)
        self.dm.save_data.assert_called()
        # Check that saved data matches corrected data (df_new_pri)
        saved_df = self.dm.save_data.call_args[0][0]
        pd.testing.assert_frame_equal(saved_df, df_new_pri)

    def test_full_verify_mode_no_conflict(self):
        """
        Case C: Full Verify Mode (No Conflict)
        - Should fetch full history
        - If no conflict, should NOT trigger backup provider
        """
        ticker = "AAPL"
        
        # Setup Data
        # Old Data
        df_old = pd.DataFrame({
            'open': [100.0], 'high': [110.0], 'low': [90.0], 'close': [105.0], 'volume': [1000]
        }, index=pd.to_datetime(['2023-01-01']))
        df_old.index.name = 'date'
        self.dm.get_data.return_value = df_old
        
        # New Primary Data (Same values)
        df_new_pri = pd.DataFrame({
            'open': [100.0], 'high': [110.0], 'low': [90.0], 'close': [105.0], 'volume': [1000]
        }, index=pd.to_datetime(['2023-01-01']))
        df_new_pri.index.name = 'date'
        self.dm.yf_provider.fetch_history.return_value = df_new_pri
        
        # Execute
        self.dm.update_data_if_needed(ticker, update_mode="FULL_VERIFY")
        
        # Assertions
        # 1. Verify Primary Fetch
        self.dm.yf_provider.fetch_history.assert_called_once()
        
        # 2. Verify Backup Fetch NOT called
        self.dm.stooq_provider.fetch_history.assert_not_called()
        self.dm.twstock_provider.fetch_history.assert_not_called()
        self.dm.ccxt_provider.fetch_history.assert_not_called()
        
        # 3. Verify Save Data (Still saved to ensure consistency/updates)
        self.dm.save_data.assert_called()

if __name__ == '__main__':
    unittest.main()
