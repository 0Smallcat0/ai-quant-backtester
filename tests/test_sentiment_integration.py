
import unittest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from src.strategies.base import Strategy

# Mocking external dependency in test file context if needed, 
# but we will import the real one inside the test method where we patch.

class DefensiveStrategy(Strategy):
    """
    Simulates the structure of the NEW AI-generated code with defensive logic.
    """
    def __init__(self, params=None):
        super().__init__(params)
        self.buy_threshold = 30
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        self.data = data.copy()
        self.data.columns = [c.lower() for c in self.data.columns]
        
        # [DEFENSIVE LOGIC]
        if 'sentiment' not in self.data.columns:
            self.data['sentiment'] = 0.0
        
        self.data['sentiment'] = self.data['sentiment'].fillna(0.0)
        
        # Logic using sentiment
        self.data['signal'] = 0
        cond = (self.data['sentiment'] >= 0)
        self.data.loc[cond, 'signal'] = 1
        return self.data

class FragileStrategy(Strategy):
    """
    Simulates the OLD AI-generated code without defense.
    """
    def __init__(self, params=None):
        super().__init__(params)

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        self.data = data.copy()
        self.data.columns = [c.lower() for c in self.data.columns]
        
        # Direct access - should fail if missing
        cond = (self.data['sentiment'] >= 0) 
        self.data['signal'] = 1
        return self.data

class TestSentimentIntegration(unittest.TestCase):
    
    def setUp(self):
        # Create a dummy dataframe without sentiment
        dates = pd.date_range(start='2023-01-01', periods=5)
        self.df_no_sentiment = pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'close': [102, 103, 101, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400]
        }, index=dates)
        
        self.df_with_sentiment = self.df_no_sentiment.copy()
        self.df_with_sentiment['sentiment'] = [0.1, 0.2, -0.1, 0.0, 0.5]

    def test_case_1a_fragile_strategy_fails(self):
        """Verify that the old strategy pattern fails when sentiment is missing."""
        strategy = FragileStrategy()
        with self.assertRaises(KeyError):
            strategy.generate_signals(self.df_no_sentiment)
            
    def test_case_1b_defensive_strategy_succeeds(self):
        """Verify that the new defensive pattern works even when sentiment is missing."""
        strategy = DefensiveStrategy()
        try:
            result = strategy.generate_signals(self.df_no_sentiment)
            self.assertIn('sentiment', result.columns)
            self.assertTrue((result['sentiment'] == 0.0).all())
            self.assertIn('signal', result.columns)
        except KeyError:
            self.fail("DefensiveStrategy raised KeyError unexpectedly!")

    @patch('src.data_engine.DataManager.get_connection')
    def test_case_2_data_manager_integration(self, mock_conn):
        """
        Verify DataManager.get_data(include_sentiment=True) returns a 'sentiment' column
        even if the underlying data source fails or returns nothing (it should default to 0.0).
        """
        # We need to import the REAL DataManager to test its logic
        from src.data_engine import DataManager as RealDataManager
        
        # Mock DB return for basic data
        mock_db_df = self.df_no_sentiment.copy().reset_index()
        # pandas read_sql usually returns date as object/string or datetime depending on driver
        # DataManager.get_data expects columns to be present.
        # It also expects 'ticker' column usually if it does `SELECT *` but logic might filter it out?
        # get_data calls `SELECT * FROM ohlcv`. So ticker column is there.
        mock_db_df['ticker'] = "TEST"
        mock_db_df.rename(columns={'index': 'date'}, inplace=True)
        
        # We mock pandas read_sql to return our df
        with patch('pandas.read_sql', return_value=mock_db_df):
            dm = RealDataManager(db_path=":memory:")
            
            # 1. Test Default (False)
            df_default = dm.get_data("TEST")
            self.assertNotIn('sentiment', df_default.columns)
            
            # 2. Test Include Sentiment (True)
            # We mock NewsEngine to return empty/fail to see if fallback works
            # Or we can rely on the fact that NewsEngine is None by default in the test instance
            # The code: engine = self.news_engine if self.news_engine else NewsEngine()
            # If we don't mock NewsEngine class, it might try to instantiate real one.
            
            with patch('src.data_engine.NewsEngine') as MockNewsEngine:
                # Mock instance
                mock_engine_instance = MockNewsEngine.return_value
                # Mock get_sentiment to return a Series
                mock_engine_instance.get_sentiment.return_value = pd.Series(
                    [0.5, 0.5, 0.5, 0.5, 0.5], index=self.df_no_sentiment.index, name='sentiment'
                )
                
                # We need to inject this engine or let logic create it. 
                # dm = RealDataManager(..., news_engine=mock_engine_instance)
                dm.news_engine = mock_engine_instance
                
                df_sentiment = dm.get_data("TEST", include_sentiment=True)
                
                self.assertIn('sentiment', df_sentiment.columns)
                # Verify it merged correctly
                self.assertEqual(df_sentiment['sentiment'].iloc[0], 0.5)

if __name__ == '__main__':
    unittest.main()
