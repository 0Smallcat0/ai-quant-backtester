import unittest
from unittest.mock import patch, MagicMock
from src.ai.llm_client import LLMClient
import os
import openai

class TestStability(unittest.TestCase):
    def setUp(self):
        # Reset Singleton for testing
        LLMClient._instance = None

    def test_singleton_persistence(self):
        """
        Case B: Verify Singleton property persists after refactor.
        """
        client1 = LLMClient()
        client2 = LLMClient()
        self.assertIs(client1, client2)

    @patch('src.ai.llm_client.OpenAI')
    def test_retry_logic(self, mock_openai):
        """
        Case A: Verify LLMClient retries on failure.
        We will mock the API to raise an error twice, then succeed.
        """
        mock_client_instance = MagicMock()
        mock_openai.return_value = mock_client_instance
        
        # Setup side_effect: Error, Error, Success
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Success"
        
        # We need to simulate a RateLimitError or similar. 
        # Since we can't easily import the exact error class without dependency, 
        # we'll use a generic Exception for now, but in implementation we target specific errors.
        # To test tenacity properly, we might need to mock the wait strategy to avoid slow tests.
        
        # For this test, we'll verify that the method is decorated with retry 
        # by checking if it handles exceptions or if we can inspect the retry attribute.
        # Alternatively, we just run it and expect it to eventually succeed if we mock properly.
        
        # Let's try to mock the create method to fail then succeed
        mock_client_instance.chat.completions.create.side_effect = [
            Exception("Rate Limit"),
            Exception("Timeout"),
            mock_response
        ]
        
        with patch.dict(os.environ, {"API_KEY": "test-key"}):
            client = LLMClient()
            
            # We need to patch the wait strategy to be instant for tests
            # This is tricky with tenacity. 
            # A simpler way is to assert that the underlying call happened multiple times.
            
            try:
                # We expect this to fail if we don't have retry, or succeed if we do (and it retries enough times)
                # But since we are TDDing, we haven't implemented retry yet.
                # So this test SHOULD FAIL initially if we expect it to handle 2 errors.
                # If we don't have retry, it will raise Exception("Rate Limit") immediately.
                response = client.get_completion([{"role": "user", "content": "hi"}])
                self.assertEqual(response, "Success")
                self.assertEqual(mock_client_instance.chat.completions.create.call_count, 3)
            except Exception as e:
                # If it raises, it means retry didn't catch it
                self.fail(f"Method failed to retry: {e}")

if __name__ == '__main__':
    unittest.main()
