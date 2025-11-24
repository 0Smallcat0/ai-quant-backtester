import pytest
import os
from unittest.mock import MagicMock
from src.ai.agent import Agent, PendingAction

class MockLLMClient:
    def __init__(self, response):
        self.response = response

    def get_completion(self, messages):
        return self.response

def test_agent_write_interception():
    # 1. Setup
    danger_file = "danger.py"
    # Ensure file doesn't exist
    if os.path.exists(danger_file):
        os.remove(danger_file)
        
    # Mock LLM response attempting to write a file
    llm_response = f'<tool code="write_file" path="{danger_file}">print("danger")</tool>'
    mock_llm = MockLLMClient(llm_response)
    agent = Agent(mock_llm)

    # 2. Action
    result = agent.chat("Create a dangerous file")

    # 3. Assertions
    
    # Assertion 1: Check return type is PendingAction
    assert isinstance(result, PendingAction), "Agent should return PendingAction for write_file"
    
    # Assertion 2: Check file was NOT created
    assert not os.path.exists(danger_file), "File should not be written automatically"
    
    # Assertion 3: Check PendingAction content
    assert result.tool_name == "write_file"
    assert result.args["path"] == danger_file
    assert result.args["content"] == 'print("danger")'

    # Cleanup (just in case)
    if os.path.exists(danger_file):
        os.remove(danger_file)
