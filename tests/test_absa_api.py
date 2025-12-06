
import pytest
import json
from unittest.mock import MagicMock
from src.analytics.sentiment.absa_analyzer import ABSAAnalyzer

@pytest.fixture
def mock_llm_client():
    mock_client = MagicMock()
    # Mock clean_code to just return the input string (assuming simple JSON)
    mock_client.clean_code.side_effect = lambda x: x 
    return mock_client

def test_absa_valid_json(mock_llm_client):
    """
    Test successful parsing of valid JSON response from LLM.
    """
    analyzer = ABSAAnalyzer(llm_client=mock_llm_client)
    
    # Mock Response
    valid_json = json.dumps({
        "Overall_Sentiment": "Positive",
        "Positive_Aspect": ["Revenue Beat", "Guidance Raise"],
        "Negative_Aspect": []
    })
    mock_llm_client.get_completion.return_value = valid_json
    
    result = analyzer.analyze("NVIDIA revenue grew.")
    
    assert result['Overall_Sentiment'] == "Positive"
    assert "Revenue Beat" in result['Positive_Aspect']
    assert not result.get('Error')

def test_absa_invalid_json(mock_llm_client):
    """
    Test handling of malformed JSON.
    """
    analyzer = ABSAAnalyzer(llm_client=mock_llm_client)
    
    # Mock malformed response
    mock_llm_client.get_completion.return_value = "This is not JSON."
    
    result = analyzer.analyze("Bad response")
    
    # Should fallback to Neutral and contain Error
    assert result['Overall_Sentiment'] == "Neutral"
    assert "Error" in result

def test_absa_wrapper_json(mock_llm_client):
    """
    Test extraction of JSON from markdown wrapper.
    """
    analyzer = ABSAAnalyzer(llm_client=mock_llm_client)
    
    json_content = json.dumps({"Overall_Sentiment": "Negative"})
    code_block = f"```json\n{json_content}\n```"
    
    # Normally clean_code handles this, but here we test the REGEX fallback in analyzer 
    # if clean_code didn't catch it or if we mock clean_code to pass raw.
    # But wait, our analyzer calls clean_code first. 
    # Let's say clean_code returns the string as is (default mock behavior above).
    # Then the REGEX in analyze() should find the brace content?
    # Actually REGEX finds { ... } 
    
    mock_llm_client.get_completion.return_value = code_block
    
    # If clean_code is identity, then `analyze` REGEX logic kicks in ?
    # Let's verify analyze logic:
    # cleaned_response = self.llm_client.clean_code(response_str)
    # match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
    
    result = analyzer.analyze("Some text")
    
    # If REGEX works, it should extract the inner JSON
    # Wait, simple REGEX {.*} might match start to end. 
    # Let's see if it parses.
    
    # Actually, if clean_code removes ```json, then we get text.
    # If clean_code is mocked to identity, the string has ```json.
    # The regex {.*} will find the json including braces. It should parse.
    
    assert result.get('Overall_Sentiment') == "Negative"

def test_empty_input(mock_llm_client):
    analyzer = ABSAAnalyzer(llm_client=mock_llm_client)
    assert analyzer.analyze("") == {}
