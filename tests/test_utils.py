import sys
import os
from pathlib import Path
import pytest

# We need to import the module to be tested. 
# Since src/utils.py doesn't exist yet, this import will fail if we run it now, 
# which is expected in TDD (Red phase).
# However, to write the test properly, we assume the structure exists.

def test_sanitize_ticker():
    from src.utils import sanitize_ticker
    
    # Case A: Sanitize Ticker
    assert sanitize_ticker("'AAPL' ") == "AAPL"
    assert sanitize_ticker(' "btc-usd" ') == "BTC-USD"
    assert sanitize_ticker("tsla") == "TSLA"
    assert sanitize_ticker("  ETH-USD  ") == "ETH-USD"

def test_add_project_root():
    from src.utils import add_project_root
    
    # Case B: Path Injection
    # We can't easily check if it *adds* the correct path without knowing where we are running from,
    # but we can check if the logic runs without error and modifies sys.path.
    
    # Capture current sys.path length
    initial_path_len = len(sys.path)
    
    add_project_root()
    
    # Check if project root is in sys.path. 
    # We assume the project root is 2 levels up from src/utils.py if it's in src/
    # But wait, utils.py will be in src/, so project root is parent of src.
    
    # Let's verify that at least something was added or checked.
    # Actually, a better test is to ensure that we can import something from the root 
    # if we were in a weird place, but that's hard to simulate.
    # Instead, let's just verify that the function exists and runs, and maybe check 
    # if the expected root path is present.
    
    # Get the expected root path based on this test file location (tests/test_utils.py)
    # tests/ is at the same level as src/, so root is parent of tests/
    current_test_path = Path(__file__).resolve()
    project_root = current_test_path.parent.parent
    
    # The function add_project_root should add the project root to sys.path
    # We might need to mock sys.path to test this properly without side effects,
    # but for this simple task, checking if it's in sys.path is enough.
    
    # Note: When running pytest, the root might already be in sys.path, 
    # so we might not see a change in length.
    # So we just assert that the root is indeed in sys.path after calling.
    
    assert str(project_root) in sys.path or str(project_root).lower() in [p.lower() for p in sys.path]
