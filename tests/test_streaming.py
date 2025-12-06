import unittest
from unittest.mock import patch, MagicMock
import os
import types
from src.ai.llm_client import LLMClient
from src.ai.agent import Agent, PendingAction

class TestStreaming(unittest.TestCase):
    @patch('src.ai.llm_client.OpenAI')
    def test_get_response_stream(self, mock_openai):
        """
        Case A: Verify get_response_stream returns a generator and yields chunks.
        """
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_openai.return_value = mock_client_instance
        
        # Mock streaming response
        mock_chunk1 = MagicMock()
        mock_chunk1.choices[0].delta.content = "Hello"
        mock_chunk2 = MagicMock()
        mock_chunk2.choices[0].delta.content = " World"
        
        mock_client_instance.chat.completions.create.return_value = [mock_chunk1, mock_chunk2]

        with patch.dict(os.environ, {"API_KEY": "test-key"}):
            client = LLMClient()
            stream = client.get_response_stream([{"role": "user", "content": "Hi"}])
            
            self.assertIsInstance(stream, types.GeneratorType)
            
            chunks = list(stream)
            self.assertEqual(chunks, ["Hello", " World"])
            
            # Verify stream=True was passed
            _, kwargs = mock_client_instance.chat.completions.create.call_args
            self.assertTrue(kwargs.get('stream'))

    @patch('src.ai.llm_client.OpenAI')
    def test_agent_chat_streaming(self, mock_openai):
        """
        Case B: Verify Agent.chat(stream=True) yields chunks.
        """
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_openai.return_value = mock_client_instance
        
        # Mock streaming response
        mock_chunk1 = MagicMock()
        mock_chunk1.choices[0].delta.content = "Thinking..."
        
        mock_client_instance.chat.completions.create.return_value = [mock_chunk1]

        with patch.dict(os.environ, {"API_KEY": "test-key"}):
            client = LLMClient()
            agent = Agent(client)
            
            # We need to mock _extract_tool_command to return None so loop finishes
            agent._extract_tool_command = MagicMock(return_value=(None, None))
            
            stream = agent.chat("Hi", stream=True)
            self.assertIsInstance(stream, types.GeneratorType)
            
            chunks = list(stream)
            self.assertIn("Thinking...", chunks)

if __name__ == '__main__':
    unittest.main()
