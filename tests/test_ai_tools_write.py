import os
import pytest
from src.ai.tools import write_file, run_shell

class TestAIToolsWrite:
    
    def setup_method(self):
        self.test_file = "test_write_output.txt"
        # Ensure clean state
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def teardown_method(self):
        # Cleanup
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_write_file_success(self):
        content = "Hello, World!"
        result = write_file(self.test_file, content)
        
        assert f"Successfully wrote to {os.path.abspath(self.test_file)}" in result
        assert os.path.exists(self.test_file)
        with open(self.test_file, 'r', encoding='utf-8') as f:
            assert f.read() == content

    def test_write_file_security(self):
        # Attempt to write outside the project root
        # Assuming the test is run from project root
        unsafe_path = "../outside_project.txt"
        result = write_file(unsafe_path, "Should not be written")
        
        assert "Access Denied" in result
        # Verify file wasn't created (though we can't easily check ../ without potentially checking real files, 
        # relying on the return message is the primary check here, plus the implementation logic)

    def test_run_shell_success(self):
        # Test a safe command
        result = run_shell('echo "test execution"')
        assert "STDOUT:" in result
        assert "test execution" in result

    def test_run_shell_blacklist(self):
        # Test blocked commands
        dangerous_commands = ["rm -rf /", "del system32", "format c:"]
        for cmd in dangerous_commands:
            result = run_shell(cmd)
            assert "Command blocked" in result
            assert "STDOUT" not in result
