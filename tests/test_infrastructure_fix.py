
import pytest
import os
import json
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from src.strategies.manager import StrategyManager
from src.data_engine import DataManager

# -------------------------------------------------------------------------
# Case A: Atomic Write
# -------------------------------------------------------------------------
def test_strategy_manager_atomic_write(tmp_path):
    """
    Verify that save_strategies uses a temporary file and then replaces the target.
    """
    # Setup
    target_file = tmp_path / "strategies.json"
    manager = StrategyManager(filepath=str(target_file))
    
    # Mock os.replace to verify it's called
    with patch("os.replace") as mock_replace:
        manager.save("TestStrategy", "print('hello')")
        
        # Check if temp file was created (we can't easily check existence inside the function 
        # without more complex mocking, but we can check if os.replace was called with a .tmp file)
        
        # Verify os.replace was called
        assert mock_replace.called
        args, _ = mock_replace.call_args
        src, dst = args
        
        # Assert source is a temp file and dest is the target file
        assert str(src).endswith(".tmp")
        assert str(dst) == str(target_file)
        
    # Verify content is actually written (integration test style)
    # We need to actually run it without mock to see if file persists
    manager.save("RealWrite", "code")
    with open(target_file, 'r') as f:
        data = json.load(f)
    assert data["RealWrite"] == "code"

# -------------------------------------------------------------------------
# Case B: Data Cleaning
# -------------------------------------------------------------------------
def test_data_manager_cleaning(tmp_path):
    """
    Verify that get_data cleans NaN and Inf values.
    """
    # Setup Mock DB
    db_path = tmp_path / "test_market_data.db"
    manager = DataManager(db_path=str(db_path))
    manager.init_db()
    
    # Create a DataFrame with dirty data
    # We will insert this directly or mock the read_sql return
    dirty_df = pd.DataFrame({
        'ticker': ['AAPL', 'AAPL', 'AAPL', 'AAPL'],
        'date': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04']),
        'open': [100.0, np.nan, 102.0, 103.0],
        'high': [105.0, 106.0, np.inf, 108.0],
        'low': [95.0, 96.0, 97.0, -np.inf],
        'close': [102.0, 104.0, 105.0, 106.0],
        'volume': [1000, 1100, 1200, 1300]
    })
    
    # Mock pd.read_sql to return dirty_df
    with patch("pandas.read_sql", return_value=dirty_df):
        clean_df = manager.get_data("AAPL")
        
        # Assertions
        # 1. Row with NaN (2023-01-02) should be removed
        # Implementation uses Smart Patching (ffill), so rows are preserved
        assert len(clean_df) == 4
        
        # Verify patching
        # Row 2 Open should be filled (100.0)
        assert clean_df.iloc[1]['open'] == 100.0
        # Row 3 High should be filled (106.0)
        assert clean_df.iloc[2]['high'] == 106.0
        # Row 4 Low should be filled (97.0)
        assert clean_df.iloc[3]['low'] == 97.0
        assert clean_df.index[0] == pd.Timestamp('2023-01-01')
        
        # Verify no NaNs or Infs remain
        assert not clean_df.isnull().values.any()
        assert not np.isinf(clean_df.select_dtypes(include=np.number)).values.any()

