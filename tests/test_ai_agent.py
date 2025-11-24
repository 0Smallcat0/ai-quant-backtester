import pytest
from unittest.mock import MagicMock, patch
from src.ai.agent import Agent

@pytest.fixture
def mock_llm_client():
    return MagicMock()

@pytest.fixture
def agent(mock_llm_client):
    # Assuming Agent takes llm_client as dependency
    return Agent(llm_client=mock_llm_client)

def test_xml_parsing(agent):
    """
    Test that the agent correctly extracts tool commands from XML tags.
    """
    response = 'Thought: I need to check files.\n<tool code="list_files">.</tool>'
    tool_name, tool_args = agent._extract_tool_command(response)
    
    assert tool_name == "list_files"
    assert tool_args == {"content": "."}

def test_xml_parsing_write_file(agent):
    """
    Test parsing of write_file with path attribute.
    """
    response = '''Thought: Create a file.
<tool code="write_file" path="src/test.py">
print("hello")
</tool>'''
    tool_name, tool_args = agent._extract_tool_command(response)
    
    assert tool_name == "write_file"
    assert tool_args == {"path": "src/test.py", "content": 'print("hello")'}

def test_xml_parsing_run_shell(agent):
    """
    Test parsing of run_shell command.
    """
    response = '<tool code="run_shell">ls -la</tool>'
    tool_name, tool_args = agent._extract_tool_command(response)
    
    assert tool_name == "run_shell"
    assert tool_args == {"content": "ls -la"}

def test_xml_parsing_no_tool(agent):
    """
    Test that the agent returns None when no tool tag is present.
    """
    response = "Here is the answer."
    tool_name, tool_args = agent._extract_tool_command(response)
    
    assert tool_name is None
    assert tool_args is None

def test_tool_execution_loop(agent, mock_llm_client):
    """
    Test the full loop: LLM calls tool -> Agent executes -> LLM sees result -> LLM answers.
    """
    # Mock LLM responses sequence:
    # 1. "I need to list files <tool...>"
    # 2. "I see the files. The answer is..." (Final answer)
    mock_llm_client.get_completion.side_effect = [
        'Thought: Check files\n<tool code="list_files">.</tool>',
        'The answer is found.'
    ]
    
    # Mock tool execution
    with patch('src.ai.agent.list_files', return_value="file1.py\nfile2.py") as mock_list:
        response = agent.chat("Hello")
        
        # Verify tool was called
        mock_list.assert_called_once_with(".")
        
        # Verify LLM was called twice
        assert mock_llm_client.get_completion.call_count == 2
        
        # Verify final response
        assert response == "The answer is found."

def test_max_steps_limit(agent, mock_llm_client):
    """
    Test that the agent stops after max_steps to prevent infinite loops.
    """
    # LLM keeps asking for tool
    mock_llm_client.get_completion.return_value = '<tool code="list_files">.</tool>'
    
    with patch('src.ai.agent.list_files', return_value="..."):
        # Set a small max_step for testing
        response = agent.chat("Loop me", max_steps=3)
        
        # Should return the last response (or a specific error message if implemented)
        # Here we assume it returns the last content or a stop message
        # For this test, we just ensure it didn't loop forever (e.g. 100 times)
        assert mock_llm_client.get_completion.call_count == 3
