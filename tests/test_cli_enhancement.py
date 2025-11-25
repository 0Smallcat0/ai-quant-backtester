import pytest
import subprocess
import sys
import re

def test_cli_alias_support():
    """
    Case A: Alias Support
    Verify that --symbol works as an alias for --ticker.
    We run the CLI with --symbol and check if it fails with 'unrecognized argument' 
    or if it proceeds (even if it fails later due to missing data, that means arg parsing worked).
    """
    # We use a dry run or just check help, but better to try running it.
    # Since we don't want to actually run a full backtest which might be slow or fail on data,
    # we can check if the error message is NOT about unrecognized arguments.
    
    # However, to be more robust, let's try to run it with a known strategy and check output.
    # We expect it to fail with "No data found" or similar if we use a dummy ticker, 
    # but NOT "unrecognized arguments: --symbol".
    
    cmd = [
        sys.executable, "src/run_backtest.py",
        "--strategy_name", "RSIStrategy",
        "--symbol", "DUMMY_TICKER",
        "--start", "2023-01-01",
        "--end", "2023-01-05"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd="d:\\ai-quant-backtester")
    
    # If alias is NOT supported, argparse prints usage and error: unrecognized arguments: --symbol
    assert "unrecognized arguments: --symbol" not in result.stderr
    
    # It might fail with "Strategy not found" or "No data found", which is fine.
    # That proves it passed the arg parsing stage.

def test_cli_logging_format():
    """
    Case B: Logger Check
    Verify that output contains timestamp and log level.
    """
    cmd = [
        sys.executable, "src/run_backtest.py",
        "--strategy_name", "RSIStrategy",
        "--ticker", "BTC-USD",
        "--start", "2023-01-01",
        "--end", "2023-01-05"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd="d:\\ai-quant-backtester")
    
    # We expect output to contain something like:
    # 2023-11-25 20:30:00,000 - INFO - ...
    # or
    # 2023-11-25 20:30:00,000 - ERROR - ...
    
    # Regex for standard logging format: YYYY-MM-DD HH:MM:SS,ms - LEVEL - Message
    # Note: default logging format might vary slightly, but we are enforcing a specific one.
    # pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - (INFO|ERROR|WARNING) -"
    
    # Since we haven't implemented it yet, this test should fail (Red phase).
    # Current output is just print statements.
    
    # We'll check for the presence of " - INFO - " or " - ERROR - " which is typical for our requested format.
    
    combined_output = result.stdout + result.stderr
    
    # In the Red phase, this assertion should fail because we are currently using print().
    assert re.search(r" - (INFO|ERROR|WARNING) - ", combined_output) is not None
