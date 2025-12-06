import pytest
from src.ai.utils_text import sanitize_agent_output, format_agent_log, split_thought_and_answer

# --- Existing Tests ---

def test_sanitize_tool_blocks():
    raw = "Here is some code:\n<tool>print('hello')</tool>\nDone."
    expected = "Here is some code:\n\nDone."
    assert sanitize_agent_output(raw) == expected

def test_sanitize_thought_lines():
    raw = "Thought: I should check the file.\nHere is the file content."
    expected = "Here is the file content."
    assert sanitize_agent_output(raw) == expected

def test_sanitize_truncation():
    raw = "123456789012345"
    max_l = 10
    sanitized = sanitize_agent_output(raw, max_len=max_l)
    assert len(sanitized) > max_l 
    assert sanitized.startswith("1234567890")
    assert "Output Truncated" in sanitized

def test_sanitize_mixed_with_truncation():
    raw = "Thought: thinking\n<tool>long log</tool>\nUser, here is a very long answer that needs truncation."
    sanitized = sanitize_agent_output(raw, max_len=10)
    assert sanitized.startswith("User, here")
    assert "Truncated" in sanitized

# --- New Tests for Formatting & Splitting ---

def test_format_agent_log_basic():
    raw = 'Thought: Checking file.\n<tool code="read_file">README.md</tool>\nTool Output: Content'
    formatted = format_agent_log(raw)
    
    assert "🤔 **思考**: Checking file." in formatted
    assert "📂 **讀取檔案**: `README.md`" in formatted
    assert "⚙️ **執行結果**: Content" in formatted

def test_format_agent_log_shell():
    raw = '<tool code="run_shell">ls -la</tool>'
    formatted = format_agent_log(raw)
    assert "💻 **執行指令**: `ls -la`" in formatted

def test_format_agent_log_generic():
    raw = '<tool>some random tool</tool>'
    formatted = format_agent_log(raw)
    assert "⚙️ **執行工具**: `some random tool`" in formatted
    
def test_format_agent_log_multiline_content():
    raw = '<tool code="write_file">Line 1\nLine 2</tool>'
    formatted = format_agent_log(raw)
    assert "💾 **寫入檔案**" in formatted
    assert "```\nLine 1\nLine 2\n```" in formatted

def test_split_thought_and_answer_simple():
    raw = "Thought: Step 1\n<tool>Act</tool>\nTool Output: done\nHere is the result."
    thought, answer = split_thought_and_answer(raw)
    
    assert "Step 1" in thought
    assert "<tool>" in thought
    assert "Here is the result." in answer
    assert "Here is the result." not in thought
    assert "Tool Output: done" in thought # It should capture tool output in thought log usually? 
    # Logic in utils: max_log_index is end of "Tool Output:".
    # So "Tool Output:" is in thought. The content " done" might be in thought or answer depending on regex.
    # Our regex was `^Tool Output:.*$`. So it captures the whole line.
    
    # If "Tool Output: done" is on one line, it is in thought.
    assert "Tool Output: done" in thought

def test_split_thought_and_answer_no_logs():
    raw = "Just direct answer."
    thought, answer = split_thought_and_answer(raw)
    assert thought == "(無詳細過程)"
    assert answer == "Just direct answer."

def test_split_thought_and_answer_late_thought():
    # Sometimes thought comes back after tool
    raw = "Thought: 1\n<tool>A</tool>\nTool Output: O\nThought: 2\nAnswer"
    thought, answer = split_thought_and_answer(raw)
    
    # Should split after "Thought: 2"
    assert "Thought: 2" in thought
    assert "Answer" in answer
    # "Answer" should NOT be in thought
    assert "Answer" not in thought

