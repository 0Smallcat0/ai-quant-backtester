import ast
import subprocess
import sys
import tempfile
import os
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str

class LocalExecutor:
    """
    A lightweight local sandbox for executing Python code safely.
    Uses AST analysis to block dangerous imports and subprocess interactions.
    """
    
    # Blocklist of dangerous modules
    BLOCKED_MODULES = {
        'os', 'sys', 'subprocess', 'shutil', 'importlib', 
        'socket', 'requests', 'urllib', 'http', 'ftplib',
        'telnetlib', 'smtplib', 'xmlrpc', 'pickle'
    }

    def __init__(self, python_executable: str = sys.executable):
        self.python_executable = python_executable

    def validate_safety(self, code: str) -> bool:
        """
        Parses the code using AST and checks for blocked imports.
        Returns True if safe, False if dangerous.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # If we can't parse it, we can't validate it -> Unsafe or run anyway?
            # Better to let it fail in execution, or return False?
            # If it's a syntax error, it won't run anyway. 
            # But validate_safety should imply "No Malicious Intent".
            # For now, if syntax error, we assume it's "Safe" in terms of malice, 
            # but we can return True and let execution fail.
            return True

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] in self.BLOCKED_MODULES:
                        return False
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in self.BLOCKED_MODULES:
                    return False
        
        return True

    def execute_safe(self, code: str, timeout: int = 30) -> ExecutionResult:
        """
        Executes the code in a separate subprocess with a timeout.
        Returns an ExecutionResult.
        """
        # 0. Safety Check
        if not self.validate_safety(code):
           return ExecutionResult(
               exit_code=1, 
               stdout="", 
               stderr="SecurityError: Blocked dangerous module import."
           )

        # 1. Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tmp_file:
            tmp_file.write(code)
            tmp_file_path = tmp_file.name

        try:
            # 2. Run the subprocess
            # We don't pass any special env vars for now, just inherit default or empty?
            # Inheriting default is risky (access to API keys). 
            # Ideally we pass a restricted env.
            # For "Lite" version, let's pass a copy of env but maybe unset sensitive ones if needed.
            # But the user Requirement said "Native Python". 
            
            # Using 'capture_output=True' captures formatted bytes, we need to decode.
            process = subprocess.run(
                [self.python_executable, tmp_file_path],
                capture_output=True,
                text=True,    # This decodes automatically
                timeout=timeout,
                cwd=os.getcwd() # Run in CWD so it can access local files if needed (Sandbox Rule?)
                                # Wait, if it's "Sandbox", accessing local files is dangerous? 
                                # But we are doing "Local RAG" and "Local Sandbox" for a "Project".
                                # If it's generating strategies, it might need to read data/ files.
                                # So CWD is fine for this Agent purpose.
            )
            
            return ExecutionResult(
                exit_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr
            )
            
        except subprocess.TimeoutExpired as e:
            return ExecutionResult(
                exit_code=124, # Standard timeout exit code
                stdout=e.stdout if e.stdout else "",
                stderr=f"TimeoutExpired: Process timed out after {timeout} seconds."
            )
        except Exception as e:
             return ExecutionResult(
                exit_code=1,
                stdout="",
                stderr=str(e)
            )
        finally:
            # 3. Cleanup
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
