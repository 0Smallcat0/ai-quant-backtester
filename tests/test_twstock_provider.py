import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.data_loader.providers.twstock_provider import TwStockProvider
import logging

class TestTwStockProvider(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_parse_ticker(self):
        provider = TwStockProvider()
        self.assertEqual(provider._parse_ticker('2330.TW'), '2330')
        self.assertEqual(provider._parse_ticker('006208.TWO'), '006208')
        self.assertEqual(provider._parse_ticker('2330'), '2330')

    @patch('src.data_loader.providers.twstock_provider.twstock.Stock')
    @patch('src.data_loader.providers.twstock_provider.time.sleep') # Mock sleep to speed up test
    def test_fetch_history(self, mock_sleep, MockStock):
        """Test fetching data from TwStock."""
        mock_stock_instance = MockStock.return_value
        
        # Mock fetch_from return value
        # twstock returns named tuples or objects. Let's mock them as dicts or objects.
        # Based on implementation, we convert to DataFrame immediately.
        # Let's simulate list of named tuples-like objects
        from collections import namedtuple
        Data = namedtuple('Data', ['date', 'capacity', 'turnover', 'open', 'high', 'low', 'close', 'change', 'transaction'])
        
        mock_data = [
            Data(
                date=pd.Timestamp('2023-01-03'), 
                capacity=1000000, 
                turnover=500000000, 
                open=500.0, 
                high=505.0, 
                low=495.0, 
                close=502.0, 
                change=2.0, 
                transaction=1000
            )
        ]
        
        mock_stock_instance.fetch_from.return_value = mock_data

        provider = TwStockProvider()
        df = provider.fetch_history('2330.TW', '2023-01-01', '2023-01-05')

        # Verify calls
        # Should call fetch_from(2023, 1)
        mock_stock_instance.fetch_from.assert_called_with(2023, 1)
        
        # Verify DataFrame
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 1)
        self.assertListEqual(list(df.columns), ['Open', 'High', 'Low', 'Close', 'Volume'])
        self.assertEqual(df.index[0], pd.Timestamp('2023-01-03'))
        self.assertEqual(df.iloc[0]['Close'], 502.0)
        self.assertEqual(df.iloc[0]['Volume'], 1000000)

    @patch('src.data_loader.providers.twstock_provider.twstock.Stock')
    @patch('src.data_loader.providers.twstock_provider.time.sleep')
    def test_fetch_history_multi_month(self, mock_sleep, MockStock):
        """Test fetching across months."""
        mock_stock_instance = MockStock.return_value
        mock_stock_instance.fetch_from.return_value = [] # Return empty for simplicity, just checking calls
        
        provider = TwStockProvider()
        try:
            provider.fetch_history('2330.TW', '2023-01-01', '2023-02-15')
        except ValueError:
            # Expected because we return empty data
            pass
            
        # Should call for Jan and Feb
        calls = mock_stock_instance.fetch_from.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].args, (2023, 1))
        self.assertEqual(calls[1].args, (2023, 2))

if __name__ == '__main__':
    unittest.main()
