import pytest
from unittest.mock import patch, MagicMock
from src.data_loader.providers.yfinance_provider import YFinanceProvider, DataFetchError
import pandas as pd

class TestEarlyData:
    @patch('yfinance.download')
    def test_fetch_pre_listing_data(self, mock_download):
        """
        Test that fetching data for a period before the stock was listed 
        returns an empty DataFrame instead of raising a DEAD_TICKER error.
        """
        provider = YFinanceProvider()
        
        # Simulate yfinance returning empty DataFrame (common for pre-listing dates)
        # This currently triggers a ValueError in the provider, which is then caught
        # and re-raised as DEAD_TICKER DataFetchError.
        mock_download.return_value = pd.DataFrame()
        
        ticker = "0056.TW"
        start_date = "2000-01-01"
        end_date = "2005-01-01"
        
        # Attempt to fetch history
        # If not fixed, this will raise DataFetchError("DEAD_TICKER: ...")
        result = provider.fetch_history(ticker, start_date, end_date)
        
        # Verification
        assert isinstance(result, pd.DataFrame)
        assert result.empty, "Should return empty DataFrame for pre-listing dates"

    @patch('yfinance.download')
    def test_fetch_post_listing_data(self, mock_download):
        """
        Test that fetching data for a valid period returns correct data.
        """
        provider = YFinanceProvider()
        
        # Mock valid data
        data = {
            'Open': [25.0, 25.5],
            'High': [26.0, 26.0],
            'Low': [24.5, 25.0],
            'Close': [25.5, 25.8],
            'Volume': [1000, 1500]
        }
        index = pd.to_datetime(["2008-01-01", "2008-01-02"])
        mock_df = pd.DataFrame(data, index=index)
        mock_download.return_value = mock_df
        
        ticker = "0056.TW"
        start_date = "2008-01-01"
        end_date = "2009-01-01"
        
        result = provider.fetch_history(ticker, start_date, end_date)
        
        assert not result.empty
        assert len(result) == 2
        assert 'Volume' in result.columns
