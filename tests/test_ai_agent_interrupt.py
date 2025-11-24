import pytest
from unittest.mock import MagicMock, patch
from src.ai.agent import Agent, PendingAction

@pytest.fixture
def mock_llm_client():
    return MagicMock()

@pytest.fixture
def agent(mock_llm_client):
    return Agent(llm_client=mock_llm_client)

def test_interrupt_write_file(agent, mock_llm_client):
    """
    Test that write_file triggers an interrupt and returns PendingAction.
    """
    # Mock LLM response requesting write_file
    mock_llm_client.get_completion.return_value = '''Thought: I need to write a file.
<tool code="write_file" path="test.py">
print("hello")
</tool>'''

    # Mock the actual tool execution to ensure it's NOT called
    with patch('src.ai.agent.write_file') as mock_write:
        result = agent.chat("Write a file")
        
        # Verify result is PendingAction
        assert isinstance(result, PendingAction)
        assert result.tool_name == "write_file"
        assert result.args == {"path": "test.py", "content": 'print("hello")'}
        assert "I need to write a file" in result.thought
        
        # Verify tool was NOT called
        mock_write.assert_not_called()

def test_auto_run_read_file(agent, mock_llm_client):
    """
    Test that read_file runs automatically and returns a string response.
    """
    # Mock LLM response requesting read_file
    # We need a sequence: 1. Request tool, 2. Final answer
    mock_llm_client.get_completion.side_effect = [
        '''Thought: Read the file.
<tool code="read_file">test.py</tool>''',
        "File content read."
    ]

    with patch('src.ai.agent.read_file', return_value="content") as mock_read:
        result = agent.chat("Read file")
        
        # Verify result is a string (final answer)
        assert isinstance(result, str)
        assert result == "File content read."
        
        # Verify tool WAS called
        mock_read.assert_called_once_with("test.py")

def test_interrupt_run_shell(agent, mock_llm_client):
    """
    Test that run_shell triggers an interrupt.
    """
    mock_llm_client.get_completion.return_value = '''Thought: Run a command.
<tool code="run_shell">ls</tool>'''

    with patch('src.ai.agent.run_shell') as mock_shell:
        result = agent.chat("Run ls")
        
        assert isinstance(result, PendingAction)
        assert result.tool_name == "run_shell"
        assert result.args == {"content": "ls"}
        
        mock_shell.assert_not_called()
