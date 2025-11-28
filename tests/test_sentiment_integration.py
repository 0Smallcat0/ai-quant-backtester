import unittest
from unittest.mock import MagicMock, patch, ANY
import pandas as pd
import os
import shutil
from src.data.news_engine import NewsEngine
from src.data_engine import DataManager

class TestSentimentIntegration(unittest.TestCase):
    def setUp(self):
        self.test_db = 'test_integration.db'
        self.cache_dir = 'test_cache'
        self.data_manager = DataManager(self.test_db)
        self.data_manager.init_db()
        
        # Ensure clean state
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        os.makedirs(self.cache_dir)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        if os.path.exists(self.test_db + '-wal'):
            os.remove(self.test_db + '-wal')
        if os.path.exists(self.test_db + '-shm'):
            os.remove(self.test_db + '-shm')
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)

    @patch('src.data.news_engine.NewsFetcher')
    @patch('src.data.news_engine.SentimentAnalyzer')
    def test_cache_logic(self, MockAnalyzer, MockFetcher):
        """Case A: Verify Cache Hit/Miss Logic"""
        # Setup Mocks
        mock_fetcher = MockFetcher.return_value
        # Fix: Add published date so NewsEngine can parse it
        mock_fetcher.fetch_headlines.return_value = [{'title': 'T1', 'summary': 'S1', 'published': 'Mon, 01 Jan 2023 00:00:00 GMT'}]
        
        mock_analyzer = MockAnalyzer.return_value
        mock_analyzer.analyze_news.return_value = 0.8
        
        engine = NewsEngine(cache_dir=self.cache_dir)
        
        # 1. First Call (Miss)
        ticker = 'AAPL'
        start_date = '2023-01-01'
        end_date = '2023-01-05'
        
        engine.get_sentiment(ticker, start_date, end_date)
        
        # Assert called
        mock_fetcher.fetch_headlines.assert_called()
        mock_analyzer.analyze_news.assert_called()
        
        # Reset mocks
        mock_fetcher.reset_mock()
        mock_analyzer.reset_mock()
        
        # 2. Second Call (Hit)
        # Note: NewsEngine now uses Parquet. 
        # Since we are using real file system in setUp/tearDown, we don't need to mock read_parquet.
        # But we need to ensure pyarrow is installed (it is in requirements).
        engine.get_sentiment(ticker, start_date, end_date)
        
        # Assert NOT called
        mock_fetcher.fetch_headlines.assert_not_called()
        mock_analyzer.analyze_news.assert_not_called()

    @patch('src.data_engine.NewsEngine')
    def test_dataframe_structure(self, MockNewsEngine):
        """Case B: Verify DataManager integrates sentiment correctly"""
        # Setup Mock NewsEngine to return a series
        mock_engine = MockNewsEngine.return_value
        dates = pd.date_range('2023-01-01', '2023-01-05')
        sentiment_series = pd.Series(0.5, index=dates, name='sentiment')
        mock_engine.get_sentiment.return_value = sentiment_series
        
        # Insert some dummy price data
        df_price = pd.DataFrame({
            'open': [100.0]*5, 'high': [105.0]*5, 'low': [95.0]*5, 'close': [102.0]*5, 'volume': [1000]*5,
            'date': dates
        })
        self.data_manager.save_data(df_price, 'AAPL')
        
        # Call get_data with include_sentiment=True
        df = self.data_manager.get_data('AAPL', include_sentiment=True)
        
        # Verify structure
        self.assertIn('sentiment', df.columns)
        self.assertEqual(len(df), 5)
        self.assertEqual(df.iloc[0]['sentiment'], 0.5)

    def test_strategy_execution(self):
        """Case C: Verify Strategy can access sentiment"""
        # This requires a bit more setup or mocking BacktestEngine's internal data loading
        # But since BacktestEngine takes a DataFrame, we just need to ensure the DataFrame passed to it has sentiment
        # and the engine doesn't strip it.
        
        from src.backtest_engine import BacktestEngine
        
        dates = pd.date_range('2023-01-01', '2023-01-05')
        df = pd.DataFrame({
            'open': [100.0]*5, 'high': [105.0]*5, 'low': [95.0]*5, 'close': [102.0]*5, 'volume': [1000]*5,
            'sentiment': [0.8, 0.8, -0.5, -0.5, 0.0] # 2 days bullish, 2 days bearish
        }, index=dates)
        
        # Create a dummy signal series
        signals = pd.Series([1.0, 1.0, 0.0, 0.0, 0.0], index=dates)
        
        engine = BacktestEngine()
        # We just want to ensure run() doesn't crash when extra columns are present
        try:
            engine.run(df, signals)
        except Exception as e:
            self.fail(f"BacktestEngine crashed with extra columns: {e}")

if __name__ == '__main__':
    unittest.main()
