import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.data_loader.providers.stooq_provider import StooqProvider
from src.data_engine import DataManager
import logging

class TestDataProviders(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    @patch('src.data_loader.providers.stooq_provider.web.DataReader')
    def test_stooq_fetch(self, mock_datareader):
        """Test fetching data from Stooq."""
        # Mock response
        mock_df = pd.DataFrame({
            'Open': [100.0, 101.0],
            'High': [102.0, 103.0],
            'Low': [99.0, 100.0],
            'Close': [101.0, 102.0],
            'Volume': [1000, 2000]
        }, index=pd.to_datetime(['2023-01-01', '2023-01-02']))
        
        # Stooq often returns reverse order, so let's simulate that if we want, 
        # but the provider should sort it. 
        # Let's return it sorted for simplicity or unsorted to test sorting.
        mock_df_unsorted = mock_df.sort_index(ascending=False)
        mock_datareader.return_value = mock_df_unsorted

        provider = StooqProvider()
        df = provider.fetch_history('AAPL', '2023-01-01', '2023-01-02')

        # Verify calls
        mock_datareader.assert_called_with('AAPL', 'stooq', start='2023-01-01', end='2023-01-02')
        
        # Verify sorting
        self.assertTrue(df.index.is_monotonic_increasing)
        self.assertEqual(len(df), 2)
        self.assertListEqual(list(df.columns), ['Open', 'High', 'Low', 'Close', 'Volume'])

    @patch('src.data_engine.YFinanceProvider')
    @patch('src.data_engine.StooqProvider')
    def test_failover_logic(self, MockStooq, MockYF):
        """Test failover from YFinance to Stooq."""
        # Setup mocks
        mock_yf_instance = MockYF.return_value
        mock_stooq_instance = MockStooq.return_value
        
        # YF fails
        mock_yf_instance.fetch_history.side_effect = Exception("YF Down")
        
        # Stooq succeeds
        mock_stooq_df = pd.DataFrame({
            'Open': [150.0], 'High': [155.0], 'Low': [149.0], 'Close': [152.0], 'Volume': [5000]
        }, index=pd.to_datetime(['2023-01-01']))
        mock_stooq_instance.fetch_history.return_value = mock_stooq_df

        # Initialize Manager (mocks are injected via class patch, but we need to ensure they are used)
        # Since we patch the classes imported in data_engine, instantiation in __init__ will use mocks.
        dm = DataManager('test.db')
        
        # We need to mock sqlite connection to avoid DB errors during fetch_data's save part
        # Or we can just inspect the internal list if we could, but fetch_data saves to DB.
        # Let's mock get_connection to return a dummy
        with patch.object(dm, 'get_connection') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            # Run fetch
            dm.fetch_data('AAPL', '2023-01-01', '2023-01-01')
            
            # Verify YF called
            mock_yf_instance.fetch_history.assert_called()
            
            # Verify Stooq called (since AAPL is US stock)
            mock_stooq_instance.fetch_history.assert_called()
            
            # Verify DB insert called (implies Stooq data was used)
            mock_cursor.executemany.assert_called()

    @patch('src.data_engine.YFinanceProvider')
    @patch('src.data_engine.StooqProvider')
    def test_no_failover_for_non_us(self, MockStooq, MockYF):
        """Test NO failover for non-US stock."""
        mock_yf_instance = MockYF.return_value
        mock_stooq_instance = MockStooq.return_value
        
        # YF fails
        mock_yf_instance.fetch_history.side_effect = Exception("YF Down")
        
        dm = DataManager('test.db')
        
        with patch.object(dm, 'get_connection') as mock_conn:
            # Run fetch for TW stock
            dm.fetch_data('2330.TW', '2023-01-01', '2023-01-01')
            
            # Verify YF called
            mock_yf_instance.fetch_history.assert_called()
            
            # Verify Stooq NOT called
            mock_stooq_instance.fetch_history.assert_not_called()

if __name__ == '__main__':
    unittest.main()
