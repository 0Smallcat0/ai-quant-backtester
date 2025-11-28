import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.data_loader.providers.ccxt_provider import CcxtProvider
import logging

class TestCcxtProvider(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_normalize_symbol(self):
        provider = CcxtProvider()
        self.assertEqual(provider._normalize_symbol('BTC-USD'), 'BTC/USDT')
        self.assertEqual(provider._normalize_symbol('ETH-USD'), 'ETH/USDT')
        self.assertEqual(provider._normalize_symbol('AAPL'), 'AAPL')

    @patch('src.data_loader.providers.ccxt_provider.ccxt.binance')
    def test_fetch_history_pagination(self, MockBinance):
        """Test fetching data with pagination."""
        mock_exchange = MockBinance.return_value
        
        # Setup mock return values for fetch_ohlcv
        # Call 1: Returns 1000 items (limit)
        # Call 2: Returns 500 items (end of data)
        # Call 3: Returns empty (stop condition)
        
        start_ts = 1672531200000 # 2023-01-01
        
        # Generate dummy data
        data_batch_1 = []
        for i in range(1000):
            ts = start_ts + i * 86400000
            data_batch_1.append([ts, 100+i, 105+i, 95+i, 102+i, 1000+i])
            
        last_ts_batch_1 = data_batch_1[-1][0]
        start_ts_batch_2 = last_ts_batch_1 + 86400000
        
        data_batch_2 = []
        for i in range(500):
            ts = start_ts_batch_2 + i * 86400000
            data_batch_2.append([ts, 2000+i, 2005+i, 1995+i, 2002+i, 2000+i])
            
        mock_exchange.fetch_ohlcv.side_effect = [data_batch_1, data_batch_2, []]

        provider = CcxtProvider()
        # Request a range that requires pagination (more than 1000 days)
        # 1000 days from 2023-01-01 is roughly late 2025.
        # Let's ask for data until 2028 to ensure we cover all 1500 mock items.
        df = provider.fetch_history('BTC-USD', '2023-01-01', '2028-01-01')

        # Verify calls
        self.assertEqual(mock_exchange.fetch_ohlcv.call_count, 2) # Should stop after batch 2 because len < limit
        
        # Verify DataFrame
        self.assertEqual(len(df), 1500)
        self.assertEqual(df.index[0], pd.Timestamp('2023-01-01'))
        self.assertListEqual(list(df.columns), ['Open', 'High', 'Low', 'Close', 'Volume'])
        
        # Verify symbol passed to ccxt
        args, kwargs = mock_exchange.fetch_ohlcv.call_args_list[0]
        self.assertEqual(args[0], 'BTC/USDT')

    @patch('src.data_loader.providers.ccxt_provider.ccxt.binance')
    def test_fetch_history_empty(self, MockBinance):
        """Test handling of empty response."""
        mock_exchange = MockBinance.return_value
        mock_exchange.fetch_ohlcv.return_value = []
        
        provider = CcxtProvider()
        with self.assertRaises(ValueError):
            provider.fetch_history('BTC-USD', '2023-01-01', '2023-01-05')

if __name__ == '__main__':
    unittest.main()
