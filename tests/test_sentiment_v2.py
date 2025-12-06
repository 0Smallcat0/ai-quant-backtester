import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from src.data.sentiment_processor import SentimentAnalyzer, DecayModel

class TestSentimentV2:
    
    @pytest.fixture
    def mock_llm_client(self):
        return MagicMock()

    def test_impact_weighting(self, mock_llm_client):
        """
        Verify that high relevance news has significantly higher score than low relevance news.
        """
        analyzer = SentimentAnalyzer(llm_client=mock_llm_client)
        
        # Case 1: High Relevance (Earnings)
        # Sentiment 0.8, Relevance 1.0 -> 0.8
        mock_response_high = '{"sentiment": 0.8, "relevance": 1.0}'
        mock_llm_client.get_completion.return_value = mock_response_high
        mock_llm_client.clean_code.return_value = mock_response_high
        
        score_high = analyzer.analyze_news([{'title': 'Earnings Beat'}], "AAPL")
        
        # Case 2: Low Relevance (Gossip)
        # Sentiment 0.8, Relevance 0.1 -> 0.08
        mock_response_low = '{"sentiment": 0.8, "relevance": 0.1}'
        mock_llm_client.get_completion.return_value = mock_response_low
        mock_llm_client.clean_code.return_value = mock_response_low
        
        score_low = analyzer.analyze_news([{'title': 'CEO Haircut'}], "AAPL")
        
        assert score_high == pytest.approx(0.8)
        assert score_low == pytest.approx(0.08)
        assert score_high > score_low * 5  # Significant difference

    def test_superposition_decay(self):
        """
        Verify linear superposition: Day 3 score should be sum of decayed Day 1 and Day 2.
        """
        # Half-life = 2 days
        # lambda = ln(2)/2 = 0.34657
        decay_model = DecayModel(half_life_days=2.0)
        dates = pd.date_range(start="2023-01-01", periods=30, freq="D")
        
        raw_scores = {
            dates[0]: 1.0, # Day 1
            dates[1]: 1.0  # Day 2
        }
        
        decayed = decay_model.apply_decay(dates, raw_scores)
        
        # Day 1 (Index 0): 1.0
        assert decayed.iloc[0] == pytest.approx(1.0)
        
        # Day 2 (Index 1):
        # Day 1 decayed 1 day: 1.0 * exp(-lambda * 1) = 1.0 * 0.7071 = 0.7071
        # Day 2 fresh: 1.0
        # Total: 1.7071
        expected_day2 = 1.0 * np.exp(-decay_model.lambda_param * 1) + 1.0
        assert decayed.iloc[1] == pytest.approx(expected_day2, rel=1e-3)
        
        # Day 3 (Index 2):
        # Day 1 decayed 2 days: 1.0 * 0.5 = 0.5
        # Day 2 decayed 1 day: 1.0 * 0.7071 = 0.7071
        # Total: 1.2071
        expected_day3 = (1.0 * np.exp(-decay_model.lambda_param * 2)) + \
                        (1.0 * np.exp(-decay_model.lambda_param * 1))
        
        assert decayed.iloc[2] == pytest.approx(expected_day3, rel=1e-3)
        
        # Verify Day 3 > Day 2 (Wait, Day 3 is 1.2, Day 2 is 1.7. It decays.)
        # The user requirement says "Day 3 > Day 2 (because Day 1 + Day 2)".
        # Wait, if Day 2 has a fresh event, Day 2 is peak.
        # Day 3 has NO event, so it should be strictly less than Day 2.
        # Unless the user meant "Day 3 score > Day 2's contribution alone".
        # Or maybe they meant "Day 3 score with superposition > Day 3 score without superposition (old logic)".
        # Old logic (overwrite): Day 2 overwrites Day 1. So Day 3 is just Day 2 decayed.
        # Day 3 (Old) = 1.0 * exp(-lambda * 1) = 0.7071
        # Day 3 (New) = 0.5 + 0.7071 = 1.2071
        # So New > Old.
        
        # Let's verify the "Day 30 approaches 0" requirement
        assert decayed.iloc[29] < 0.01

