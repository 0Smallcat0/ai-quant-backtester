import os
import subprocess

from functools import lru_cache

@lru_cache(maxsize=10)
def list_files(start_path: str = ".") -> str:
    """
    List files in a directory recursively, returning a tree structure string.
    Filters out common ignored directories.
    """
    start_path = os.path.abspath(start_path)
    output = []
    ignore_dirs = {'.git', '__pycache__', 'venv', 'env', '.idea', '.vscode'}
    
    for root, dirs, files in os.walk(start_path):
        # Filter dirs in-place and sort
        dirs[:] = sorted([d for d in dirs if d not in ignore_dirs])
        files.sort()
        
        rel_path = os.path.relpath(root, start_path)
        
        if rel_path == ".":
            # Root files
            for f in files:
                output.append(f)
        else:
            # Subdirectories
            depth = rel_path.count(os.sep)
            indent = "  " * depth
            dir_name = os.path.basename(root)
            output.append(f"{indent}{dir_name}/")
            
            file_indent = "  " * (depth + 1)
            for f in files:
                output.append(f"{file_indent}{f}")
                
    return "\n".join(output)

def _validate_path(file_path: str) -> bool:
    """
    Validate that the file path is within the current working directory.
    Returns True if valid, False otherwise.
    """
    root_dir = os.getcwd()
    abs_path = os.path.abspath(file_path)
    
    try:
        common = os.path.commonpath([root_dir, abs_path])
    except ValueError:
        # Can happen on Windows if paths are on different drives
        return False
        
    return common == root_dir

@lru_cache(maxsize=100)
def read_file(file_path: str, max_lines: int = 5000) -> str:
    """
    Read a file safely.
    - Enforces that file is within the current working directory (project root).
    - Checks for binary extensions.
    - Truncates content if it exceeds max_lines.
    """
    if not _validate_path(file_path):
        return "Error: Access Denied - Path traversal detected."
        
    abs_path = os.path.abspath(file_path)
        
    # Binary Check
    ext = os.path.splitext(abs_path)[1].lower()
    if ext in {'.png', '.jpg', '.db', '.sqlite', '.pyc'}:
        return "Error: Binary file detected. Cannot read text."
        
    # Read
    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        try:
            with open(abs_path, 'r', encoding='latin-1') as f:
                lines = f.readlines()
        except Exception:
             return "Error: Binary file detected. Cannot read text."
    except Exception as e:
        return f"Error: Could not read file. {str(e)}"
        
    total_lines = len(lines)
    if total_lines > max_lines:
        half = max_lines // 2
        truncated_msg = f"\n... [Content Truncated: File has {total_lines} lines] ...\n"
        content = "".join(lines[:half]) + truncated_msg + "".join(lines[-half:])
    else:
        content = "".join(lines)
        
    return content

def write_file(file_path: str, content: str) -> str:
    """
    Write content to a file safely.
    - Enforces that file is within the current working directory.
    - Overwrites existing files.
    - Clears read_file and list_files cache to ensure consistency.
    """
    if not _validate_path(file_path):
        return "Error: Access Denied - Path traversal detected."
        
    abs_path = os.path.abspath(file_path)
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        # Clear caches
        read_file.cache_clear()
        list_files.cache_clear()
        
        return f"Successfully wrote to {abs_path}"
    except Exception as e:
        return f"Error: Could not write to file. {str(e)}"

def run_shell(command: str) -> str:
    """
    Execute a shell command safely.
    - Blocks dangerous commands.
    - Returns STDOUT or STDERR.
    - Enforces 30s timeout.
    - Truncates output to last 2000 chars.
    """
    BLOCKED_COMMANDS = {
        'rm', 'del', 'mv', 'shutdown', 'format', 'mkfs', 'dd',
        'wget', 'curl', 'chmod', 'chown', 'ssh', 'scp', 
        'top', 'htop', 'nano', 'vim', 'vi', 'reboot'
    }
    
    # Simple check: first word of the command
    cmd_parts = command.strip().split()
    if not cmd_parts:
        return "Error: Empty command."
        
    base_cmd = cmd_parts[0].lower()
    if base_cmd in BLOCKED_COMMANDS:
        return f"Error: Command blocked. '{base_cmd}' is not allowed."
        
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        output = result.stdout if result.returncode == 0 else result.stderr
        prefix = "STDOUT" if result.returncode == 0 else "STDERR"
        
        MAX_OUTPUT_LENGTH = 2000
        if len(output) > MAX_OUTPUT_LENGTH:
            output = f"\n... [Output Truncated]\n{output[-MAX_OUTPUT_LENGTH:]}"
            
        return f"{prefix}:\n{output}"
            
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"Error: Command execution failed. {str(e)}"
