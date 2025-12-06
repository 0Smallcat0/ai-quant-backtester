
import pytest
from unittest.mock import MagicMock, patch
import torch
import json
from src.analytics.sentiment.absa_analyzer import ABSAAnalyzer

@pytest.fixture
def mock_absa_setup():
    with patch('src.analytics.sentiment.absa_analyzer.AutoTokenizer') as mock_tokenizer, \
         patch('src.analytics.sentiment.absa_analyzer.AutoModelForCausalLM') as mock_model:
        
        # Setup Tokenizer
        mock_tokenizer.from_pretrained.return_value = MagicMock()
        mock_tokenizer_instance = mock_tokenizer.from_pretrained.return_value
        
        # Determine device for return_tensors logic if needed, but mock usually handles it.
        # simple mock for inputs conversion
        mock_tokenizer_instance.return_value = {'input_ids': torch.tensor([1])}
        # mock decode
        mock_tokenizer_instance.decode.return_value = """
### Instruction:
...
### Response:
{
    "Overall_Sentiment": "Positive",
    "Positive_Aspect": ["Revenue Growth"],
    "Negative_Aspect": []
}
"""

        # Setup Model
        mock_model.from_pretrained.return_value = MagicMock()
        mock_model_instance = mock_model.from_pretrained.return_value
        
        # Mock generate
        mock_model_instance.generate.return_value = torch.tensor([[1, 2, 3]]) # Dummy output tokens
        
        yield mock_tokenizer, mock_model

def test_absa_initialization(mock_absa_setup):
    analyzer = ABSAAnalyzer()
    assert analyzer.model is not None

def test_absa_analyze_valid(mock_absa_setup):
    analyzer = ABSAAnalyzer()
    text = "Revenue is up."
    result = analyzer.analyze(text)
    
    assert result['Overall_Sentiment'] == "Positive"
    assert "Revenue Growth" in result['Positive_Aspect']

def test_absa_analyze_empty(mock_absa_setup):
    analyzer = ABSAAnalyzer()
    result = analyzer.analyze("")
    assert result == {}

def test_absa_json_parse_error(mock_absa_setup):
    mock_tok, mock_mod = mock_absa_setup
    # Override decode to return bad JSON
    mock_tok.from_pretrained.return_value.decode.return_value = "### Response:\n Invalid JSON"
    
    analyzer = ABSAAnalyzer()
    result = analyzer.analyze("Bad text")
    assert result['Overall_Sentiment'] == "Neutral"
    assert  result['Error'] == "Parse Failure"
