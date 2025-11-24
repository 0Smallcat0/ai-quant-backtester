import unittest
from unittest.mock import MagicMock, patch
from src.ai.agent import Agent
from src.ai.llm_client import LLMClient

class TestAgentIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_llm_client = MagicMock(spec=LLMClient)
        self.agent = Agent(self.mock_llm_client)

    def test_agent_chat_simple_response(self):
        """Test simple question answering without tools."""
        user_input = "Hello, who are you?"
        expected_response = "I am an AI assistant."
        
        # Mock LLM response
        self.mock_llm_client.get_completion.return_value = expected_response
        
        response = self.agent.chat(user_input)
        
        self.assertEqual(response, expected_response)
        self.mock_llm_client.get_completion.assert_called_once()

    @patch('src.ai.agent.list_files')
    def test_agent_chat_with_tool_execution(self, mock_list_files):
        """Test ReAct flow: Thought -> Tool -> Result -> Answer."""
        user_input = "Please list the files in src folder."
        
        # Define the sequence of LLM responses
        # Round 1: Agent decides to use the tool
        round1_response = 'Thought: The user wants to see files.\n<tool code="list_files">src</tool>'
        # Round 2: Agent sees the tool output and gives final answer
        round2_response = "Here are the files: main.py, utils.py"
        
        self.mock_llm_client.get_completion.side_effect = [round1_response, round2_response]
        
        # Mock tool output
        mock_list_files.return_value = "main.py\nutils.py"
        
        response = self.agent.chat(user_input)
        
        # Assertion 1: Verify list_files tool was called with "src"
        mock_list_files.assert_called_once_with("src")
        
        # Assertion 2: Verify Agent.chat returned the final response
        self.assertEqual(response, round2_response)
        
        # Verify LLM was called twice
        self.assertEqual(self.mock_llm_client.get_completion.call_count, 2)
        
        # Optional: Verify the conversation history passed to LLM in the second call
        # The second call should include the tool output
        second_call_args = self.mock_llm_client.get_completion.call_args_list[1]
        messages_passed = second_call_args[0][0] # first arg is messages list
        
        # Check if the last message in history before the final answer generation contains tool output
        # Structure: System -> User -> Assistant (Tool Call) -> User (Tool Output)
        self.assertEqual(messages_passed[-1]['role'], 'user')
        self.assertIn("Tool Output:", messages_passed[-1]['content'])
        self.assertIn("main.py", messages_passed[-1]['content'])

if __name__ == '__main__':
    unittest.main()
