import unittest
from unittest.mock import patch, MagicMock
import os
import time
from src.ai.llm_client import LLMClient

class TestClientOptimization(unittest.TestCase):
    def setUp(self):
        # Reset Singleton instance before each test
        if hasattr(LLMClient, "_instance"):
            LLMClient._instance = None

    @patch('src.ai.llm_client.OpenAI')
    def test_singleton_pattern(self, mock_openai):
        """
        Case A: Verify Singleton pattern.
        """
        with patch.dict(os.environ, {"API_KEY": "test-key"}):
            client1 = LLMClient()
            client2 = LLMClient()
            self.assertIs(client1, client2, "LLMClient should be a Singleton")
            
            # Verify init is not called multiple times if we were tracking it, 
            # but for now just checking identity is enough.

    @patch('src.ai.llm_client.OpenAI')
    def test_caching_mechanism(self, mock_openai):
        """
        Case B: Verify Cache Hit.
        """
        mock_client_instance = MagicMock()
        mock_openai.return_value = mock_client_instance
        
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "cached_code"
        mock_client_instance.chat.completions.create.return_value = mock_completion

        with patch.dict(os.environ, {"API_KEY": "test-key"}):
            client = LLMClient()
            
            # First call - should hit API
            start_time = time.time()
            result1 = client.generate_strategy_code("repeat prompt")
            duration1 = time.time() - start_time
            
            # Second call - should hit Cache
            start_time = time.time()
            result2 = client.generate_strategy_code("repeat prompt")
            duration2 = time.time() - start_time
            
            self.assertEqual(result1, result2)
            
            # Verify API was called ONLY ONCE
            self.assertEqual(mock_client_instance.chat.completions.create.call_count, 1, "API should be called only once due to cache")
            
            # Verify speed (optional, but good for sanity)
            # In a mock environment, both are fast, but call_count is the real test.

if __name__ == '__main__':
    unittest.main()
