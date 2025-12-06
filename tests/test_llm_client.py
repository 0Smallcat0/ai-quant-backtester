import unittest
from unittest.mock import patch, MagicMock
from src.ai.llm_client import LLMClient

class TestLLMClient(unittest.TestCase):
    @patch('os.getenv')
    @patch('src.ai.llm_client.OpenAI')
    def test_generate_strategy_code(self, mock_openai, mock_getenv):
        # Mock environment variable
        mock_getenv.return_value = "test-key"
        
        # Mock the API response
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "class GeneratedStrategy(Strategy): pass"
        
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client_instance
        
        client = LLMClient()
        code = client.generate_strategy_code("Buy when RSI < 30")
        
        self.assertEqual(code, "class GeneratedStrategy(Strategy): pass")
        mock_client_instance.chat.completions.create.assert_called_once()

if __name__ == '__main__':
    unittest.main()
