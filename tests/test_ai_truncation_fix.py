
import pytest
from unittest.mock import MagicMock, patch
from src.ai.llm_client import LLMClient
from src.strategies.loader import StrategyLoader, StrategyLoadError

class TestAITruncationFix:
    def setup_method(self):
        # Reset Singleton state
        LLMClient._instance = None
        self.loader = StrategyLoader()
        self.llm_client = LLMClient(api_key="dummy")

    def test_auto_continuation(self):
        """Test Case 1: Client should auto-continue when finish_reason is 'length'"""
        
        # Patch the OpenAI class imported in llm_client.py
        with patch('src.ai.llm_client.OpenAI') as MockOpenAI:
            mock_client_instance = MagicMock()
            MockOpenAI.return_value = mock_client_instance
            
            # Re-initialize LLMClient to pick up the mock
            self.llm_client = LLMClient(api_key="dummy")
            # Force client re-creation (since __init__ might verify key)
            self.llm_client.client = mock_client_instance

            # Create two mock responses
            mock_response_1 = MagicMock()
            mock_response_1.id = "run_1"
            mock_response_1.choices = [MagicMock()]
            mock_response_1.choices[0].message.content = "def part_one():\n    pass"
            mock_response_1.choices[0].finish_reason = "length" # Simulate truncation

            mock_response_2 = MagicMock()
            mock_response_2.id = "run_2"
            mock_response_2.choices = [MagicMock()]
            mock_response_2.choices[0].message.content = "\ndef part_two():\n    pass"
            mock_response_2.choices[0].finish_reason = "stop" # Finished

            # Side effect: return response 1 then response 2
            mock_client_instance.chat.completions.create.side_effect = [mock_response_1, mock_response_2]

            prompt = "Generate code"
            
            full_code = self.llm_client.generate_strategy_code(prompt)
            
            # The client should have concatenated the parts.
            assert "def part_one():" in full_code
            assert "def part_two():" in full_code
            
            # Verify it called create twice
            assert mock_client_instance.chat.completions.create.call_count == 2
            
            # Verify the second call included the previous content and continuation prompt
            call_args_list = mock_client_instance.chat.completions.create.call_args_list
            second_call_messages = call_args_list[1].kwargs['messages']
            
            assert len(second_call_messages) >= 4
            assert second_call_messages[-2]['role'] == 'assistant'
            assert second_call_messages[-2]['content'] == "def part_one():\n    pass"
            assert second_call_messages[-1]['role'] == 'user'
            assert "Continue generating" in second_call_messages[-1]['content']
            
            # [NEW] Verify that the system prompt actually contains the Negative Constraints
            # This detects the "Split Brain" issue where we use the wrong prompt
            system_message = second_call_messages[0]
            assert system_message['role'] == 'system'
            # We expect "NEGATIVE CONSTRAINTS" to be in the system prompt if we are using the correct one
            assert "NEGATIVE CONSTRAINTS" in system_message['content']

    def test_loader_truncation_detection(self):
        """Test Case 2: Loader should detect SyntaxError and provide friendly message if truncated"""
        
        # Incomplete code (SyntaxError: unterminated string literal)
        truncated_code = """
from src.strategies.base import Strategy
class MyStrategy(Strategy):
    def init(self):
        self.label = "Buy
"""
        # This code ends with "Buy -> Unterminated string literal
        
        with pytest.raises(StrategyLoadError) as excinfo:
            self.loader.load_from_code(truncated_code)
        
        # We expect a friendly error message
        error_str = str(excinfo.value).lower()
        assert "truncated" in error_str
