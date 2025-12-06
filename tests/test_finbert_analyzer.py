
import pytest
from unittest.mock import MagicMock, patch
import torch
import numpy as np
from src.analytics.sentiment.finbert_analyzer import FinBERTAnalyzer

@pytest.fixture
def mock_finbert_setup():
    with patch('src.analytics.sentiment.finbert_analyzer.BertTokenizer') as mock_tokenizer, \
         patch('src.analytics.sentiment.finbert_analyzer.BertForSequenceClassification') as mock_model:
        
        # Setup Tokenizer mock
        mock_tokenizer.from_pretrained.return_value = MagicMock()
        mock_tokenizer_instance = mock_tokenizer.from_pretrained.return_value
        # Mock encode_plus to return dict with tensors
        mock_tokenizer_instance.encode_plus.return_value = {
            'input_ids': torch.tensor([1, 2, 3]),
            'attention_mask': torch.tensor([1, 1, 1])
        }

        # Setup Model mock
        mock_model.from_pretrained.return_value = MagicMock()
        mock_model_instance = mock_model.from_pretrained.return_value
        
        # Determine device (match what the class does)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        mock_model_instance.to.return_value = mock_model_instance # chained call
        
        # Mock forward pass return
        mock_output = MagicMock()
        # Logits for [Neutral, Positive, Negative] -> let's say High Positive
        # Softmax of [0, 10, 0] is approx [0, 1, 0]
        mock_output.logits = torch.tensor([[0.0, 10.0, 0.0]])
        mock_model_instance.return_value = mock_output
        
        yield mock_tokenizer, mock_model

def test_finbert_initialization(mock_finbert_setup):
    analyzer = FinBERTAnalyzer()
    assert analyzer.batch_size == 16
    assert analyzer.model is not None

def test_finbert_prediction(mock_finbert_setup):
    analyzer = FinBERTAnalyzer()
    texts = ["Stocks are soaring!"]
    
    # We need to mock the DataLoader iteration or the internal components seamlessly
    # Since DataLoader wraps our Dataset, and Dataset uses the tokenizer, 
    # and the loop calls the model...
    
    # Actually, mocking imports inside the test file is cleaner for integration simulation
    # but the fixture above mocks the classes.
    # The real DataLoader will start workers. On Windows this can be tricky with mocks if num_workers > 0.
    # We set num_workers=0 in code, so it should be fine.

    results = analyzer.predict(texts)
    
    assert len(results) == 1
    # based on our logits [0, 10, 0], positive should be highest
    assert results[0]['Positive'] > results[0]['Neutral']
    assert results[0]['Positive'] > results[0]['Negative']

def test_finbert_empty_input(mock_finbert_setup):
    analyzer = FinBERTAnalyzer()
    results = analyzer.predict([])
    assert results == []
