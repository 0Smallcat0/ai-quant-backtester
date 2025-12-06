
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime
import sys
import os
sys.path.append(os.getcwd())
from src.data_engine import DataManager
from src.config.settings import settings

class TestDatePassing(unittest.TestCase):
    def setUp(self):
        self.mock_db_path = ":memory:"
        self.dm = DataManager(db_path=self.mock_db_path)
        self.dm.yf_provider = MagicMock()
        self.dm.get_connection = MagicMock() # Mock DB to avoid errors

    def test_full_verify_respects_user_date(self):
        """Test that FULL_VERIFY mode uses the user-provided start_date."""
        ticker = "BTC-USD"
        user_start = "2020-01-01"
        
        # Mock _calc_smart_start to return something irrelevant (system shouldn't rely on it for FULL_VERIFY default override behavior if we want strictness, 
        # but current logic implementation plan says we will use user input)
        self.dm._calc_smart_start = MagicMock(return_value="2000-01-01")
        
        # We need to mock settings.DATA_UPDATE_MODE or pass custom mode
        # The method under test: update_data_if_needed
        
        # Mock get_data to raise ValueError so it goes to "save new data" path (simplest path)
        self.dm.get_data = MagicMock(side_effect=ValueError("No data"))
        self.dm.save_data = MagicMock()
        
        # Mock fetch_history return
        mock_df = pd.DataFrame({'Open': [100]}, index=pd.to_datetime(["2020-01-02"]))
        self.dm.yf_provider.fetch_history.return_value = mock_df
        
        self.dm.update_data_if_needed(ticker=ticker, update_mode="FULL_VERIFY", start_date=user_start)
        
        # Assert fetch_history was called with 2020-01-01 (or close to it), NOT 2000-01-01
        # The key fix is that it shouldn't be hardcoded "2000-01-01"
        args, _ = self.dm.yf_provider.fetch_history.call_args
        called_start_date = args[1]
        
        self.assertEqual(called_start_date, user_start, f"FULL_VERIFY should use user start date {user_start}, got {called_start_date}")

    def test_incremental_respects_user_date(self):
        """Test that INCREMENTAL uses user date if it's provided and we want to fill gaps."""
        ticker = "BTC-USD"
        user_start = "2020-01-01"
        
        # Scenario: DB has data until 2000-01-05. Smart start says 2000-01-06.
        # User says 2020. We want max(2020, 2000) -> 2020.
        
        self.dm._calc_smart_start = MagicMock(return_value="2000-01-06")
        self.dm.fetch_data = MagicMock()
        
        self.dm.update_data_if_needed(ticker=ticker, update_mode="INCREMENTAL", start_date=user_start)
        
        self.dm.fetch_data.assert_called_once()
        args, kwargs = self.dm.fetch_data.call_args
        # fetch_data(ticker, start_date=..., ...)
        called_start = kwargs.get('start_date')
        
        self.assertEqual(called_start, user_start, f"INCREMENTAL should use user start {user_start}, got {called_start}")

if __name__ == '__main__':
    unittest.main()
