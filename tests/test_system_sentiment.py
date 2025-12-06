
import pytest
from unittest.mock import MagicMock, patch
from src.data.sentiment_processor import SentimentAnalyzer
from src.analytics.sentiment.sentiment_signal import SentimentFactorEngine

@pytest.fixture
def mock_components():
    with patch('src.data.sentiment_processor.FinBERTAnalyzer') as mock_finbert_cls, \
         patch('src.data.sentiment_processor.ABSAAnalyzer') as mock_absa_cls:
        
        mock_finbert = mock_finbert_cls.return_value
        mock_absa = mock_absa_cls.return_value
        
        yield mock_finbert, mock_absa

def test_filter_mechanics_neutral_skip(mock_components):
    """
    Case 1: Neutral news (Prob > 0.85) should NOT trigger LLM call.
    """
    mock_finbert, mock_absa = mock_components
    
    # Setup FinBERT to return high neutral score
    # Neutral > 0.85
    mock_finbert.predict.return_value = [
        {'Neutral': 0.90, 'Positive': 0.05, 'Negative': 0.05}
    ]
    
    analyzer = SentimentAnalyzer()
    # Ensure mode is set to local_hybrid
    analyzer.mode = "local_hybrid"
    
    news = [{'title': 'Boring', 'summary': 'Nothing happened'}]
    score = analyzer.analyze_news(news, "AAPL")
    
    # Assertions
    # 1. FinBERT was called
    mock_finbert.predict.assert_called_once()
    
    # 2. ABSA was NOT called (Cost Saving)
    mock_absa.analyze_batch.assert_not_called()
    
    # 3. Score should be 0 because it was filtered as noise
    assert score == 0.0

def test_filter_mechanics_low_polarity_skip(mock_components):
    """
    Case 1b: Emotion is weak (Polarity < 0.5) should NOT trigger LLM call.
    Polarity = Pos - Neg
    Ex: Pos=0.4, Neg=0.2, Neu=0.4. Polarity = 0.2 < 0.5
    """
    mock_finbert, mock_absa = mock_components
    
    mock_finbert.predict.return_value = [
        {'Neutral': 0.4, 'Positive': 0.4, 'Negative': 0.2} # Polarity 0.2
    ]
    
    analyzer = SentimentAnalyzer()
    analyzer.mode = "local_hybrid"
    
    news = [{'title': 'Mild', 'summary': 'Slightly good'}]
    score = analyzer.analyze_news(news, "AAPL")
    
    # ABSA NOT called
    mock_absa.analyze_batch.assert_not_called()
    
    # Score should be pure FinBERT score (0.2) or handling specific logic
    # The requirement says "rely on FinBERT score solely".
    # 0.6 * 0.2 + 0.4 * 0 (since no ABSA) = 0.12 * Boost(1.0) = 0.12
    assert abs(score - 0.12) < 0.01

def test_filter_mechanics_strong_emotion_trigger(mock_components):
    """
    Case 2: Strong emotion should trigger LLM.
    Pos=0.8, Neg=0.1. Polarity = 0.7 > 0.5
    """
    mock_finbert, mock_absa = mock_components
    
    mock_finbert.predict.return_value = [
        {'Neutral': 0.1, 'Positive': 0.8, 'Negative': 0.1}
    ]
    # Mock ABSA result
    mock_absa.analyze_batch.return_value = [
        {'Overall_Sentiment': 'Positive', 'Positive_Aspect': ['Growth'], 'Negative_Aspect': []}
    ]
    
    analyzer = SentimentAnalyzer()
    analyzer.mode = "local_hybrid"
    
    news = [{'title': 'Exciting', 'summary': 'Huge beat'}]
    score = analyzer.analyze_news(news, "AAPL")
    
    # ABSA CALLED
    mock_absa.analyze_batch.assert_called_once()
    assert score > 0.5

def test_impact_weighting():
    """
    Case 3: Verify SentimentFactorEngine correctly dampens signal based on relevance.
    """
    engine = SentimentFactorEngine()
    
    # High sentiment (0.8) but low relevance (0.2)
    # Expected: 0.8 * 0.2 = 0.16
    
    news_items = [{'relevance_score': 0.2}]
    sentiment_score = 0.8
    
    final_signal = engine.compute_signal(news_items, sentiment_score)
    
    assert abs(final_signal - 0.16) < 0.001

def test_impact_weighting_high():
    """
    Case 4: High sentiment (0.8) AND high relevance (1.0)
    """
    engine = SentimentFactorEngine()
    news_items = [{'relevance_score': 1.0}]
    sentiment_score = 0.8
    
    final_signal = engine.compute_signal(news_items, sentiment_score)
    assert abs(final_signal - 0.8) < 0.001
