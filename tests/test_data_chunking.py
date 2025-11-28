import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.data_engine import DataManager
from src.config.settings import settings

class TestDataChunking:
    
    def test_chunk_generation_logic(self):
        """
        Case A: Verify chunk calculation logic.
        Input: 2000-01-01 to 2020-12-31, MAX_CHUNK_YEARS=5
        Expected: 2000-2004, 2005-2009, 2010-2014, 2015-2019, 2020-2020 (or similar depending on implementation)
        """
        # Mock YFinanceProvider to verify fetch_history calls
        with patch('src.data_engine.YFinanceProvider') as MockProvider:
            mock_instance = MockProvider.return_value
            mock_instance.fetch_history.return_value = pd.DataFrame() # Return empty DF
            
            dm = DataManager(db_path=":memory:")
            
            # Set MAX_CHUNK_YEARS to 5 for this test
            with patch.object(settings, 'MAX_CHUNK_YEARS', 5):
                dm.fetch_data("AAPL", start_date="2000-01-01", end_date="2020-12-31")
                
                # Check how many times fetch_history was called
                # Total years = 21 (2000 to 2020 inclusive)
                # Chunks: 
                # 1. 2000-2004 (5 years)
                # 2. 2005-2009 (5 years)
                # 3. 2010-2014 (5 years)
                # 4. 2015-2019 (5 years)
                # 5. 2020-2020 (1 year)
                # Total calls should be 5.
                
                assert mock_instance.fetch_history.call_count == 5, f"Expected 5 chunks, got {mock_instance.fetch_history.call_count}"
                
                # Verify arguments of the first call
                args, kwargs = mock_instance.fetch_history.call_args_list[0]
                # fetch_history(ticker, start_date, end_date)
                # args[0] is ticker, args[1] is start, args[2] is end
                
                assert args[1] == "2000-01-01"
                
                # Verify arguments of the last call
                args, kwargs = mock_instance.fetch_history.call_args_list[-1]
                assert args[1] == "2020-01-01"
