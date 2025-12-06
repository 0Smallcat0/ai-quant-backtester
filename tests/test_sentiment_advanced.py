import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from src.data.sentiment_processor import SentimentAnalyzer, DecayModel

class TestSentimentAdvanced:
    
    @pytest.fixture
    def mock_llm_client(self):
        return MagicMock()

    def test_relevance_parsing_and_calculation(self, mock_llm_client):
        """
        Test that the analyzer correctly parses 'relevance' and calculates
        final_score = sentiment * relevance.
        """
        analyzer = SentimentAnalyzer(llm_client=mock_llm_client)
        
        # Mock LLM response with new JSON structure
        mock_response = """
        {
            "reason": "Strong earnings beat.",
            "sentiment": 0.8,
            "relevance": 0.5
        }
        """
        mock_llm_client.get_completion.return_value = mock_response
        mock_llm_client.clean_code.return_value = mock_response
        
        # We need to mock the news_list input
        news_list = [{'title': 'Test News', 'summary': 'Summary'}]
        
        # Run analysis
        # Note: This test expects the refactored logic. 
        # Current logic might return 0.0 or fail to parse 'relevance' if not updated.
        score = analyzer.analyze_news(news_list, "AAPL")
        
        # Expected: 0.8 * 0.5 = 0.4
        # If the code isn't updated yet, this might fail, which is correct for TDD.
        assert score == pytest.approx(0.4)

    def test_low_relevance_impact(self, mock_llm_client):
        """
        Test that high sentiment but low relevance results in a low score.
        """
        analyzer = SentimentAnalyzer(llm_client=mock_llm_client)
        
        mock_response = """
        {
            "reason": "CEO changed hairstyle.",
            "sentiment": 0.9,
            "relevance": 0.1
        }
        """
        mock_llm_client.get_completion.return_value = mock_response
        mock_llm_client.clean_code.return_value = mock_response
        
        score = analyzer.analyze_news([{'title': 'Gossip', 'summary': '...' }], "AAPL")
        
        # Expected: 0.9 * 0.1 = 0.09
        assert score == pytest.approx(0.09)

class TestDecaySuperposition:
    
    def test_superposition_logic(self):
        """
        Test that scores from multiple days stack up (linear superposition).
        """
        # Half-life of 1 day for easy calculation
        # lambda = ln(2) / 1 = 0.693
        decay_model = DecayModel(half_life_days=1.0)
        
        dates = pd.date_range(start="2023-01-01", periods=5, freq="D")
        
        # Two events:
        # Day 0: Score 1.0
        # Day 1: Score 1.0
        raw_scores = {
            dates[0]: 1.0,
            dates[1]: 1.0
        }
        
        decayed_series = decay_model.apply_decay(dates, raw_scores)
        
        # Day 0: 1.0 (Event 1)
        assert decayed_series.iloc[0] == pytest.approx(1.0)
        
        # Day 1: 
        # Event 1 decayed 1 day: 1.0 * 0.5 = 0.5
        # Event 2 fresh: 1.0
        # Total: 1.5
        assert decayed_series.iloc[1] == pytest.approx(1.5)
        
        # Day 2:
        # Event 1 decayed 2 days: 1.0 * 0.25 = 0.25
        # Event 2 decayed 1 day: 1.0 * 0.5 = 0.5
        # Total: 0.75
        assert decayed_series.iloc[2] == pytest.approx(0.75)

    def test_decay_performance_vectorization(self):
        """
        Ensure the implementation can handle a larger range without error.
        """
        decay_model = DecayModel(half_life_days=2.0)
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        raw_scores = {
            dates[0]: 1.0,
            dates[10]: 0.5,
            dates[50]: -0.8
        }
        
        result = decay_model.apply_decay(dates, raw_scores)
        assert len(result) == 100
        assert not result.isna().any()
