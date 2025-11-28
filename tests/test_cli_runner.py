import subprocess
import sys
import os
import json
import pytest
import pandas as pd

# Define the path to the CLI runner script
CLI_SCRIPT = os.path.join("src", "run_backtest.py")

# Add src to python path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.data_engine import DataManager
from src.config.settings import settings

@pytest.fixture(scope="module")
def setup_data():
    """
    Populate DB with dummy data for testing.
    """
    dm = DataManager(db_path=str(settings.DB_PATH))
    dm.init_db()
    
    # Create dummy data for BTC-USD
    dates = pd.date_range(start="2020-01-01", end="2020-04-01", freq="D")
    data = []
    price = 10000.0
    for date in dates:
        price += 100 if date.day % 2 == 0 else -90
        data.append({
            "ticker": "BTC-USD",
            "date": date.strftime("%Y-%m-%d"),
            "open": price,
            "high": price + 50,
            "low": price - 50,
            "close": price + 10,
            "volume": 1000
        })
    
    # Insert into DB
    conn = dm.get_connection()
    cursor = conn.cursor()
    cursor.executemany('''
        INSERT OR REPLACE INTO ohlcv (ticker, date, open, high, low, close, volume)
        VALUES (:ticker, :date, :open, :high, :low, :close, :volume)
    ''', data)
    conn.commit()
    conn.close()
    
    yield
    
    # Cleanup (optional, maybe keep for other tests)

def test_run_strategy_success(setup_data):
    """
    Case A: Run a valid strategy (e.g., 'MA_Crossover') and check for success.
    """
    # Ensure the script exists before running (it won't exist yet in TDD phase, so this might fail if we run it now, which is expected)
    # But for the test logic, we assume we are testing the script.
    
    cmd = [
        sys.executable,
        CLI_SCRIPT,
        "--strategy_name", "MovingAverageStrategy",
        "--ticker", "BTC-USD",
        "--start", "2020-01-01",
        "--end", "2020-04-01",
        "--json"
    ]
    
    # We expect this to fail if src/run_backtest.py doesn't exist yet.
    # In a real TDD cycle, we'd create the file first or expect the test to error out on file not found.
    # Here we'll just try to run it.
    
    if not os.path.exists(CLI_SCRIPT):
        pytest.fail(f"CLI script not found at {CLI_SCRIPT}")

    # [FIX] Add project root to PYTHONPATH for the subprocess
    env = os.environ.copy()
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    
    assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
    
    # Check if output is valid JSON
    try:
        output_data = json.loads(result.stdout)
        assert "cagr" in output_data
        assert "max_drawdown" in output_data
        assert "total_return" in output_data
    except json.JSONDecodeError:
        pytest.fail(f"Output was not valid JSON: {result.stdout}")

def test_run_strategy_invalid():
    """
    Case B: Run an invalid strategy and check for error.
    """
    if not os.path.exists(CLI_SCRIPT):
        pytest.fail(f"CLI script not found at {CLI_SCRIPT}")

    cmd = [
        sys.executable,
        CLI_SCRIPT,
        "--strategy_name", "NonExistentStrategy",
        "--ticker", "BTC-USD"
    ]
    
    # [FIX] Add project root to PYTHONPATH for the subprocess
    env = os.environ.copy()
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    
    assert result.returncode != 0, "Script should have failed for invalid strategy"
    assert result.returncode != 0, "Script should have failed for invalid strategy"
    assert "StrategyLoadError" in result.stderr or "not found" in result.stderr

def test_run_strategy_no_json_flag(setup_data):
    """
    Test running without --json flag to ensure human readable output contains keywords.
    """
    if not os.path.exists(CLI_SCRIPT):
        pytest.fail(f"CLI script not found at {CLI_SCRIPT}")

    cmd = [
        sys.executable,
        CLI_SCRIPT,
        "--strategy_name", "MovingAverageStrategy",
        "--ticker", "BTC-USD",
        "--start", "2020-01-01",
        "--end", "2020-02-01"
    ]
    
    # [FIX] Add project root to PYTHONPATH for the subprocess
    env = os.environ.copy()
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    
    assert result.returncode == 0
    assert "cagr" in result.stdout
    assert "max_drawdown" in result.stdout
