import os
import pytest
from src.ai.tools import list_files, read_file

def test_list_files_structure(tmp_path):
    """
    Test that list_files returns .py files but excludes .git directory.
    """
    # Setup
    (tmp_path / "test.py").touch()
    (tmp_path / "other.txt").touch()
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").touch()
    
    # Action
    result = list_files(str(tmp_path))
    
    # Assert
    assert "test.py" in result
    assert ".git" not in result

def test_read_file_success(tmp_path, monkeypatch):
    """
    Test that read_file correctly returns file content.
    """
    # Setup
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "hello.txt"
    f.write_text("Hello World", encoding="utf-8")
    
    # Action
    content = read_file("hello.txt")
    
    # Assert
    assert content == "Hello World"

def test_read_file_security_traversal(tmp_path, monkeypatch):
    """
    Test that read_file prevents path traversal attacks.
    """
    monkeypatch.chdir(tmp_path)
    # Action
    # Attempt to read a file using parent directory traversal
    result = read_file("../secret.txt")
    
    # Assert
    # Should return an error message, not raise an exception
    assert "Access Denied" in result or "Security Violation" in result

def test_read_file_truncation(tmp_path, monkeypatch):
    """
    Test that read_file truncates content when it exceeds max_lines.
    """
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "large.txt"
    # Create 6000 lines
    lines = ["Line " + str(i) for i in range(6000)]
    f.write_text("\n".join(lines), encoding="utf-8")
    
    # Action
    # Assuming read_file accepts max_lines as an argument
    content = read_file("large.txt", max_lines=5000)
    
    # Assert
    assert len(content.splitlines()) < 6000
    assert "Truncated" in content

def test_read_binary_file(tmp_path, monkeypatch):
    """
    Test that read_file handles binary files gracefully.
    """
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "image.png"
    # Write some binary data
    f.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    
    # Action
    content = read_file("image.png")
    
    # Assert
    assert "Binary file" in content
