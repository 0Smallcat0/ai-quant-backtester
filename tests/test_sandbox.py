import pytest
import shutil
from src.ai.sandbox.local_executor import LocalExecutor, ExecutionResult

class TestLocalSandbox:
    def setup_method(self):
        self.executor = LocalExecutor()

    def test_validate_safety_valid(self):
        code = "import pandas as pd\nprint('hello')"
        assert self.executor.validate_safety(code) is True

    def test_validate_safety_invalid_import(self):
        code = "import os\nos.system('echo hack')"
        assert self.executor.validate_safety(code) is False

    def test_validate_safety_invalid_from_import(self):
        code = "from shutil import rmtree"
        assert self.executor.validate_safety(code) is False

    def test_execute_safe_basic(self):
        code = "print('output')"
        result = self.executor.execute_safe(code)
        assert result.exit_code == 0
        assert "output" in result.stdout

    def test_execute_safe_syntax_error(self):
        code = "print('open"
        result = self.executor.execute_safe(code)
        assert result.exit_code != 0
        assert "SyntaxError" in result.stderr

    def test_execute_safe_timeout(self):
        # Infinite loop
        code = "while True: pass"
        result = self.executor.execute_safe(code, timeout=2) # 2 seconds
        assert result.exit_code != 0
        assert "timed out" in result.stderr
