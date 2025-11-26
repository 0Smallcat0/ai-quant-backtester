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
        # We need to test the internal logic of fetch_data or extract the chunking logic to a helper method.
        # Since we are refactoring fetch_data, let's assume we will use a loop that we can verify via mocking yf.download.
        
        # Mock yf.download to avoid actual network calls
        with patch('src.data_engine.yf.download') as mock_download:
            mock_download.return_value = pd.DataFrame() # Return empty DF to avoid processing
            
            dm = DataManager(db_path=":memory:")
            
            # Set MAX_CHUNK_YEARS to 5 for this test
            with patch.object(settings, 'MAX_CHUNK_YEARS', 5):
                dm.fetch_data("AAPL", start_date="2000-01-01", end_date="2020-12-31")
                
                # Check how many times download was called
                # Total years = 21 (2000 to 2020 inclusive)
                # Chunks: 
                # 1. 2000-2004 (5 years)
                # 2. 2005-2009 (5 years)
                # 3. 2010-2014 (5 years)
                # 4. 2015-2019 (5 years)
                # 5. 2020-2020 (1 year)
                # Total calls should be 5.
                
                # If the old logic (1 year per chunk) was used, it would be 21 calls.
                
                assert mock_download.call_count == 5, f"Expected 5 chunks, got {mock_download.call_count}"
                
                # Verify arguments of the first call
                args, kwargs = mock_download.call_args_list[0]
                # yf.download(ticker, start=..., end=...)
                # Note: yf.download 'end' is exclusive usually, but let's check what we pass.
                # In our code we pass string dates.
                
                # We expect the first chunk to start at 2000-01-01
                assert kwargs['start'] == "2000-01-01"
                
                # Verify arguments of the last call
                args, kwargs = mock_download.call_args_list[-1]
                assert kwargs['start'] == "2020-01-01"
