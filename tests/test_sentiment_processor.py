import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from src.data.sentiment_processor import SentimentAnalyzer, DecayModel

class TestSentimentProcessor(unittest.TestCase):
    def setUp(self):
        self.analyzer = SentimentAnalyzer()
        self.decay_model = DecayModel()

    def test_mock_llm_parsing(self):
        """Case C: Verify correct parsing of LLM JSON response"""
        # Setup Mock
        mock_client = MagicMock()
        mock_client.get_completion.return_value = '{"score": 0.8, "reason": "Good earnings"}'
        mock_client.clean_code.side_effect = lambda x: x
        
        # Inject mock client into analyzer via DI
        analyzer = SentimentAnalyzer(llm_client=mock_client)
        
        news_list = [{'title': 'T1', 'summary': 'S1'}]
        score = analyzer.analyze_news(news_list, ticker='AAPL')
        
        self.assertEqual(score, 0.8)

    def test_broken_json_handling(self):
        """Case D: Verify handling of broken JSON from LLM"""
        # Setup Mock to return non-JSON
        mock_client = MagicMock()
        mock_client.get_completion.return_value = 'Sentiment is positive'
        mock_client.clean_code.side_effect = lambda x: x
        
        analyzer = SentimentAnalyzer(llm_client=mock_client)
        
        news_list = [{'title': 'T1', 'summary': 'S1'}]
        score = analyzer.analyze_news(news_list, ticker='AAPL')
        
        # Should default to 0.0
        self.assertEqual(score, 0.0)

    def test_prompt_truncation(self):
        """Case B: Verify prompt truncation to 4000 chars"""
        mock_client = MagicMock()
        mock_client.get_completion.return_value = '{"score": 0.0, "reason": "Neutral"}'
        mock_client.clean_code.side_effect = lambda x: x
        
        analyzer = SentimentAnalyzer(llm_client=mock_client)

        # Create long news
        long_text = "A" * 5000
        news_list = [{'title': 'Long Title', 'summary': long_text}]
        
        analyzer.analyze_news(news_list, ticker='AAPL')
        
        # Check arguments passed to LLM
        call_args = mock_client.get_completion.call_args
        # Implementation uses keyword argument 'messages'
        kwargs = call_args[1]
        messages = kwargs['messages']
        user_content = messages[1]['content']
        
        self.assertLess(len(user_content), 5000) 

    def test_exponential_decay_math(self):
        """Case A: Verify exponential decay math"""
        # Half-life = 3 days -> lambda = ln(2)/3 approx 0.231
        # Day 1: 1.0
        # Day 2 (1 day later): 1.0 * exp(-0.231 * 1) = 0.7937
        # Day 4 (3 days later): 1.0 * exp(-0.231 * 3) = 0.5
        
        dates = pd.date_range(start='2023-01-01', end='2023-01-05')
        raw_scores = {
            pd.Timestamp('2023-01-01'): 1.0
        }
        
        decayed_series = self.decay_model.apply_decay(dates, raw_scores)
        
        # Day 1
        self.assertAlmostEqual(decayed_series.loc['2023-01-01'], 1.0, places=2)
        
        # Day 2
        expected_day2 = 1.0 * np.exp(-np.log(2)/3 * 1)
        self.assertAlmostEqual(decayed_series.loc['2023-01-02'], expected_day2, places=2)
        
        # Day 4 (Jan 4th) is 3 days after Jan 1st
        expected_day4 = 0.5
        self.assertAlmostEqual(decayed_series.loc['2023-01-04'], expected_day4, places=2)

if __name__ == '__main__':
    unittest.main()
