import unittest
from unittest.mock import patch, MagicMock
import os
from src.ai.llm_client import LLMClient

class TestLLMParams(unittest.TestCase):
    @patch('src.ai.llm_client.OpenAI')
    def test_unlimited_tokens_and_params(self, mock_openai):
        """
        Case A: Verify max_tokens is NOT in payload.
        Case B: Verify temperature=0.0 and top_p=0.9.
        """
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_openai.return_value = mock_client_instance
        
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "code"
        mock_client_instance.chat.completions.create.return_value = mock_completion

        # Execute with patched environment
        with patch.dict(os.environ, {"API_KEY": "test-key"}):
            client = LLMClient()
            client.generate_strategy_code("test prompt")

        # Verify
        call_args = mock_client_instance.chat.completions.create.call_args
        _, kwargs = call_args
        
        # Case A: max_tokens should NOT be present
        self.assertNotIn('max_tokens', kwargs, "max_tokens should NOT be in the API call")
        
        # Case B: Check sampling parameters
        from src.config.settings import settings
        self.assertEqual(kwargs.get('temperature'), settings.DEFAULT_TEMPERATURE, f"Temperature should be {settings.DEFAULT_TEMPERATURE}")
        self.assertEqual(kwargs.get('top_p'), settings.DEFAULT_TOP_P, f"Top_p should be {settings.DEFAULT_TOP_P}")

if __name__ == '__main__':
    unittest.main()
