import pytest
from src.ai.llm_client import LLMClient
import ast

class TestAISanitization:
    
    @pytest.fixture
    def client(self):
        # We don't need a real API key for testing clean_code
        return LLMClient(api_key="sk-test")

    def test_sanitize_full_width_comma(self, client):
        """Test replacement of full-width comma '，' with ASCII comma ','"""
        raw_code = "x = [1， 2， 3]"
        cleaned = client.clean_code(raw_code)
        assert cleaned == "x = [1, 2, 3]"

    def test_sanitize_full_width_colon(self, client):
        """Test replacement of full-width colon '：' with ASCII colon ':'"""
        raw_code = "def my_func()："
        cleaned = client.clean_code(raw_code)
        assert cleaned == "def my_func():"

    def test_sanitize_full_width_parentheses(self, client):
        """Test replacement of full-width parentheses '（）'"""
        raw_code = "print（'hello'）"
        cleaned = client.clean_code(raw_code)
        assert cleaned == "print('hello')"

    def test_sanitize_full_width_brackets(self, client):
        """Test replacement of full-width brackets '【】'"""
        raw_code = "x = 【1, 2】"
        cleaned = client.clean_code(raw_code)
        assert cleaned == "x = [1, 2]"
    
    def test_sanitize_full_width_quotes(self, client):
        """Test replacement of full-width quotes"""
        raw_code = "s = “hello”"
        cleaned = client.clean_code(raw_code)
        assert cleaned == 's = "hello"'

    def test_complex_sanitization(self, client):
        """Test a more complex scenario with mixed full-width characters that should be proper python"""
        # A snippet that would be valid python if punctuation was ASCII
        raw_code = """
def strategy(data)：
    signals = 【】
    for i in range（len（data））：
        if data[i] > 100：
            signals.append（1）
        else：
            signals.append（0）
    return signals
"""
        cleaned = client.clean_code(raw_code)
        
        # Verify it parses as valid Python AST
        try:
            ast.parse(cleaned)
        except SyntaxError as e:
            pytest.fail(f"Cleaned code failed to parse: {e}")

        assert "def strategy(data):" in cleaned
        assert "signals = []" in cleaned
        assert "range(len(data))" in cleaned

    def test_strip_thought_process(self, client):
        """Test removal of 'Thought:' lines"""
        raw_code = """Thought: This is a thought process.
Thought: Another thought line.
def my_func():
    return True
"""
        cleaned = client.clean_code(raw_code)
        assert "Thought:" not in cleaned
        assert "def my_func():" in cleaned
        assert cleaned.strip() == "def my_func():\n    return True"

    def test_unwrap_tool_tags(self, client):
        """Test unwrapping of <tool> tags"""
        raw_code = """<tool code="write_file">
class MyStrategy:
    pass
</tool>"""
        cleaned = client.clean_code(raw_code)
        assert "<tool" not in cleaned
        assert "</tool>" not in cleaned
        assert "class MyStrategy:" in cleaned

    def test_combined_leakage_and_markdown(self, client):
        """Test removal of Thought lines, Tool tags, and Markdown blocks together"""
        raw_code = """Thought: Thinking...
<tool>
```python
def test():
    return 1
```
</tool>
"""
        cleaned = client.clean_code(raw_code)
        assert "Thought:" not in cleaned
        assert "<tool>" not in cleaned
        assert "```" not in cleaned
        assert "def test():" in cleaned

