import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from src.data_loader.providers.yfinance_provider import YFinanceProvider
from src.data_loader.providers.stooq_provider import StooqProvider
from src.data_loader.providers.twstock_provider import TwStockProvider
from src.data_loader.providers.ccxt_provider import CcxtProvider
import logging

class TestDataConsistency(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def _verify_dataframe_standard(self, df: pd.DataFrame, provider_name: str):
        """Helper to verify DataFrame standard."""
        # Check columns
        expected_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        self.assertListEqual(list(df.columns), expected_cols, f"{provider_name} columns mismatch")
        
        # Check index
        self.assertTrue(isinstance(df.index, pd.DatetimeIndex), f"{provider_name} index is not DatetimeIndex")
        self.assertTrue(df.index.is_monotonic_increasing, f"{provider_name} index is not sorted ascending")
        
        # Check dtypes
        for col in expected_cols:
            self.assertTrue(pd.api.types.is_float_dtype(df[col]), f"{provider_name} column {col} is not float")

    @patch('src.data_loader.providers.yfinance_provider.yf.download')
    def test_yfinance_consistency(self, mock_download):
        # Mock YFinance returning lowercase columns and unsorted index
        data = {
            'open': [100.0, 101.0],
            'high': [105.0, 106.0],
            'low': [95.0, 96.0],
            'close': [102.0, 103.0],
            'volume': [1000.0, 2000.0]
        }
        df_mock = pd.DataFrame(data, index=pd.to_datetime(['2023-01-02', '2023-01-01']))
        mock_download.return_value = df_mock
        
        provider = YFinanceProvider()
        df = provider.fetch_history('AAPL', '2023-01-01', '2023-01-02')
        
        # YFinanceProvider currently capitalizes columns, but does it sort index?
        # yf.download usually returns sorted, but let's see if provider enforces it.
        # The provider code: df.columns = [str(c).capitalize() ...]
        # It does NOT explicitly sort index.
        
        self._verify_dataframe_standard(df, "YFinanceProvider")

    @patch('src.data_loader.providers.stooq_provider.web.DataReader')
    def test_stooq_consistency(self, mock_datareader):
        # Mock Stooq returning descending index (typical for Stooq)
        data = {
            'Open': [101.0, 100.0],
            'High': [106.0, 105.0],
            'Low': [96.0, 95.0],
            'Close': [103.0, 102.0],
            'Volume': [2000.0, 1000.0]
        }
        df_mock = pd.DataFrame(data, index=pd.to_datetime(['2023-01-02', '2023-01-01']))
        mock_datareader.return_value = df_mock
        
        provider = StooqProvider()
        df = provider.fetch_history('AAPL', '2023-01-01', '2023-01-02')
        
        self._verify_dataframe_standard(df, "StooqProvider")

    @patch('src.data_loader.providers.twstock_provider.twstock.Stock')
    @patch('src.data_loader.providers.twstock_provider.time.sleep')
    def test_twstock_consistency(self, mock_sleep, MockStock):
        # Mock TwStock returning named tuples
        from collections import namedtuple
        Data = namedtuple('Data', ['date', 'capacity', 'turnover', 'open', 'high', 'low', 'close', 'change', 'transaction'])
        
        # Unsorted dates
        mock_data = [
            Data(pd.Timestamp('2023-01-02'), 2000, 0, 101.0, 106.0, 96.0, 103.0, 0, 0),
            Data(pd.Timestamp('2023-01-01'), 1000, 0, 100.0, 105.0, 95.0, 102.0, 0, 0)
        ]
        MockStock.return_value.fetch_from.return_value = mock_data
        
        provider = TwStockProvider()
        df = provider.fetch_history('2330.TW', '2023-01-01', '2023-01-02')
        
        self._verify_dataframe_standard(df, "TwStockProvider")

    @patch('src.data_loader.providers.ccxt_provider.ccxt.binance')
    def test_ccxt_consistency(self, MockBinance):
        # Mock CCXT returning list of lists
        # [timestamp, open, high, low, close, volume]
        # Unsorted timestamps? CCXT usually sorted, but let's test robustness.
        ts1 = int(pd.Timestamp('2023-01-01').timestamp() * 1000)
        ts2 = int(pd.Timestamp('2023-01-02').timestamp() * 1000)
        
        # Mock returning unsorted (if possible) or just verify standard
        mock_data = [
            [ts2, 101.0, 106.0, 96.0, 103.0, 2000.0],
            [ts1, 100.0, 105.0, 95.0, 102.0, 1000.0]
        ]
        MockBinance.return_value.fetch_ohlcv.return_value = mock_data
        
        provider = CcxtProvider()
        df = provider.fetch_history('BTC-USD', '2023-01-01', '2023-01-02')
        
        # CcxtProvider currently does NOT explicitly sort index.
        # If fetch_ohlcv returns unsorted, the DF will be unsorted.
        # We should fix this in the provider if the test fails.
        
        self._verify_dataframe_standard(df, "CcxtProvider")

if __name__ == '__main__':
    unittest.main()
