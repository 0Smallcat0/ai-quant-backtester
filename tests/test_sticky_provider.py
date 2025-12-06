import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.data_engine import DataManager

@pytest.fixture
def mock_yf_provider():
    return MagicMock()

@pytest.fixture
def mock_stooq_provider():
    return MagicMock()

@pytest.fixture
def data_manager(mock_yf_provider, mock_stooq_provider, tmp_path):
    db_file = tmp_path / "test.db"
    dm = DataManager(db_path=str(db_file))
    dm.init_db() # Initialize tables
    dm.yf_provider = mock_yf_provider
    dm.stooq_provider = mock_stooq_provider
    return dm

def test_sticky_provider_failover(data_manager, mock_yf_provider, mock_stooq_provider):
    """
    Test that if YFinance fails on the first chunk, 
    the engine switches to Stooq for the RETRY of the first chunk 
    AND stays with Stooq for the second chunk.
    """
    # Setup
    ticker = "AAPL"
    # Chunk 1 (2020) fails on YF, succeeds on Stooq
    # Chunk 2 (2021) should use Stooq immediately
    
    # Mock Data Responses
    df_chunk = pd.DataFrame({
        'open': [100.0], 'high': [105.0], 'low': [99.0], 'close': [102.0], 'volume': [1000]
    }, index=pd.to_datetime(['2020-01-02']))
    df_chunk.index.name = 'date'
    
    # YF fails completely
    mock_yf_provider.fetch_history.side_effect = Exception("YF Timeout")
    
    # Stooq succeeds
    mock_stooq_provider.fetch_history.return_value = df_chunk
    
    # We need to ensure _get_backup_provider returns our mock
    # AAPL is US stock, so it should return stooq_provider
    
    # Execute (Use 2 year range to force 2 chunks if chunk size is 1, 
    # but default is 5 years. We need to force chunking or assume loop runs once?
    # Actually, we can just patch params to force multiple chunks.
    # The default MAX_CHUNK_YEARS is likely 5 or 10. Let's force it to 1 year for this test.)
    
    with patch('src.config.settings.settings.MAX_CHUNK_YEARS', 1):
         with patch('src.data_engine.settings.MAX_CHUNK_YEARS', 1): # Patch where it's imported/used
            data_manager.fetch_data(ticker, start_date="2020-01-01", end_date="2021-12-31")
            
    # Verification
    # 1. YF should be called exactly once (Chunk 1)
    assert mock_yf_provider.fetch_history.call_count == 1
    
    # 2. Stooq should be called twice:
    #    - Once for Chunk 1 (Retry)
    #    - Once for Chunk 2 (Sticky)
    assert mock_stooq_provider.fetch_history.call_count == 2
    
    # Check arguments
    # Chunk 1 Retry
    mock_stooq_provider.fetch_history.assert_any_call(ticker, "2020-01-01", "2020-12-31")
    # Chunk 2 Sticky
    mock_stooq_provider.fetch_history.assert_any_call(ticker, "2021-01-01", "2021-12-31")

def test_fast_fail_yftzmissing_error():
    """
    Test that YFinanceProvider raises DataFetchError immediately on YFTzMissingError.
    We need to import the class to test it directly or test via DataManager?
    The instruction says 'Implement Fast Fail in ... yfinance_provider.py'.
    So we should test the provider directly.
    """
    from src.data_loader.providers.yfinance_provider import YFinanceProvider, DataFetchError
    
    provider = YFinanceProvider()
    
    # Mock yf.download to raise the specific error
    # We can simulate it with a generic exception containing the string if we can't import the actual error
    with patch('yfinance.download', side_effect=Exception("YFTzMissingError: 'America/New_York'")):
        with pytest.raises(DataFetchError) as excinfo:
            provider.fetch_history("FAIL", "2020-01-01", "2020-01-02")
        
        assert "Data quality failed" not in str(excinfo.value) # Should be the error we raised or wrapped?
        # Wait, the plan says "raise DataFetchError".
        # If we raise DataFetchError, we skip retries.
        
    # Verify no retries (mock call count == 1)
    with patch('yfinance.download', side_effect=Exception("YFTzMissingError: 'America/New_York'")) as mock_download:
        try:
             provider.fetch_history("FAIL", "2020-01-01", "2020-01-02")
        except:
             pass
        assert mock_download.call_count == 1

