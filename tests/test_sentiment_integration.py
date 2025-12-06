
import pytest
from unittest.mock import MagicMock, patch
from src.data.sentiment_processor import SentimentAnalyzer

@pytest.fixture
def mock_pipeline():
    with patch('src.data.sentiment_processor.FinBERTAnalyzer') as mock_finbert_cls, \
         patch('src.data.sentiment_processor.ABSAAnalyzer') as mock_absa_cls:
        
        # Setup FinBERT instance
        mock_finbert = mock_finbert_cls.return_value
        # Mock predict: Return list of dicts {Neutral, Positive, Negative}
        mock_finbert.predict.return_value = [
            {'Neutral': 0.1, 'Positive': 0.8, 'Negative': 0.1}, # High Conf Pos
            {'Neutral': 0.9, 'Positive': 0.05, 'Negative': 0.05} # Noise (should be filtered)
        ]
        
        # Setup ABSA instance
        mock_absa = mock_absa_cls.return_value
        # Mock analyze_batch: Return list of dicts
        mock_absa.analyze_batch.return_value = [
            {'Overall_Sentiment': 'Positive', 'Positive_Aspect': ['Growth'], 'Negative_Aspect': []}
        ]
        
        yield mock_finbert, mock_absa

def test_integration_flow(mock_pipeline):
    mock_finbert, mock_absa = mock_pipeline
    
    analyzer = SentimentAnalyzer()
    
    news_list = [
        {'title': 'Good News', 'summary': 'Profits up'},
        {'title': 'Boring News', 'summary': 'Nothing happened'}
    ]
    
    score = analyzer.analyze_news(news_list, "AAPL")
    
    # Verification
    # 1. FinBERT called with all items
    assert mock_finbert.predict.call_count == 1
    args, _ = mock_finbert.predict.call_args
    assert len(args[0]) == 2
    
    # 2. ABSA called only with "Good News" (filtered noise)
    assert mock_absa.analyze_batch.call_count == 1
    args_absa, _ = mock_absa.analyze_batch.call_args
    assert len(args_absa[0]) == 1
    assert "Good News" in args_absa[0][0]
    
    # 3. Score Calculation
    # FinBERT Score: 0.8 - 0.1 = 0.7
    # ABSA Score: 1.0 (Positive)
    # Aspect Boost: 1.2
    # Combined: (0.6*0.7 + 0.4*1.0) * 1.2 = (0.42 + 0.4) * 1.2 = 0.82 * 1.2 = 0.984
    
    assert score > 0.9

def test_integration_all_noise(mock_pipeline):
    mock_finbert, mock_absa = mock_pipeline
    
    # Override FinBERT to return only noise
    mock_finbert.predict.return_value = [
        {'Neutral': 0.9, 'Positive': 0.05, 'Negative': 0.05}
    ]
    
    analyzer = SentimentAnalyzer()
    score = analyzer.analyze_news([{'title': 'Boring', 'summary': '..'}] , "AAPL")
    
    # ABSA should NOT be called
    mock_absa.analyze_batch.assert_not_called()
    assert score == 0.0
