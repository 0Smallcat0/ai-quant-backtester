import unittest
import pandas as pd
import numpy as np
from src.strategies.presets import SentimentRSIStrategy

class TestSentimentRSI(unittest.TestCase):
    def setUp(self):
        # Create sample data
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        self.data = pd.DataFrame({
            'open': np.random.randn(100) + 100,
            'high': np.random.randn(100) + 105,
            'low': np.random.randn(100) + 95,
            'close': np.random.randn(100) + 100,
            'volume': np.random.randint(100, 1000, 100)
        }, index=dates)
        
        # Add sentiment column
        self.data['sentiment'] = 0.0

    def test_sentiment_filter(self):
        """Case A: Verify Sentiment Filter (RSI < 30 but Sentiment < 0 -> No Buy)"""
        strategy = SentimentRSIStrategy(period=14, buy_threshold=30, sell_threshold=70, sentiment_threshold=0.0)
        
        # Mock RSI to be oversold (e.g., 20)
        # We can mock _calculate_rsi or just manipulate the data so RSI calculation results in < 30
        # Easier to mock _calculate_rsi for precise control
        
        # Create a mock _calculate_rsi method
        original_calculate_rsi = strategy._calculate_rsi
        strategy._calculate_rsi = lambda series, period: pd.Series([20] * len(series), index=series.index)
        
        # Set sentiment to negative
        self.data['sentiment'] = -0.5
        
        signals = strategy.generate_signals(self.data)
        
        # Should NOT buy because sentiment is negative
        self.assertTrue((signals['signal'] != 1).all(), "Should not buy when sentiment is negative")
        
        # Restore method
        strategy._calculate_rsi = original_calculate_rsi

    def test_normal_buy(self):
        """Case B: Verify Normal Buy (RSI < 30 and Sentiment >= 0 -> Buy)"""
        strategy = SentimentRSIStrategy(period=14, buy_threshold=30, sell_threshold=70, sentiment_threshold=0.0)
        
        # Mock RSI to be oversold
        original_calculate_rsi = strategy._calculate_rsi
        strategy._calculate_rsi = lambda series, period: pd.Series([20] * len(series), index=series.index)
        
        # Set sentiment to positive
        self.data['sentiment'] = 0.2
        
        signals = strategy.generate_signals(self.data)
        
        # Should buy
        self.assertTrue((signals['signal'] == 1).all(), "Should buy when sentiment is positive")
        
        # Restore method
        strategy._calculate_rsi = original_calculate_rsi

    def test_missing_column_graceful_fallback(self):
        """Case C: Verify Missing Column Graceful Fallback"""
        strategy = SentimentRSIStrategy(period=14, buy_threshold=30, sell_threshold=70, sentiment_threshold=0.0)
        
        # Drop sentiment column
        data_no_sentiment = self.data.drop(columns=['sentiment'])
        
        # Mock RSI to be oversold
        original_calculate_rsi = strategy._calculate_rsi
        strategy._calculate_rsi = lambda series, period: pd.Series([20] * len(series), index=series.index)
        
        signals = strategy.generate_signals(data_no_sentiment)
        
        # Should buy (fallback to sentiment=0.0)
        self.assertTrue((signals['signal'] == 1).all(), "Should buy when sentiment column is missing (fallback)")
        
        # Restore method
        strategy._calculate_rsi = original_calculate_rsi

if __name__ == '__main__':
    unittest.main()
