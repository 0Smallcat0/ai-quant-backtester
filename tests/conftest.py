import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.config.settings import settings

@pytest.fixture
def mock_price_data():
    """
    Generates a standard OHLCV DataFrame for testing.
    Includes:
    - Normal data
    - NaN values (to test cleaning)
    - Zero values (to test validation)
    """
    dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
    data = {
        "open": [100.0, 101.0, 102.0, np.nan, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0],
        "high": [105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0],
        "low": [95.0, 96.0, 97.0, 98.0, 99.0, 100.0, 101.0, 102.0, 103.0, 104.0],
        "close": [102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0],
        "volume": [1000, 1100, 1200, 0, 1400, 1500, 1600, 1700, 1800, 1900]
    }
    df = pd.DataFrame(data, index=dates)
    df.index.name = "date"
    return df

@pytest.fixture
def mock_settings(monkeypatch):
    """
    Isolate test environment configuration.
    """
    test_db_path = settings.BASE_DIR / "tests" / "data" / "test_market_data.db"
    test_db_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "DATA_DIR", test_db_path.parent)
    monkeypatch.setattr(settings, "DB_PATH", test_db_path)
    return settings
