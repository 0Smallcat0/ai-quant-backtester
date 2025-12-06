import pytest
from unittest.mock import patch, MagicMock
from src.data_engine import DataManager
import pandas as pd

@pytest.fixture
def data_engine(tmp_path):
    db_path = str(tmp_path / "test_yfinance.db")
    engine = DataManager(db_path)
    engine.init_db()
    return engine

def test_fetch_data_auto_adjust_logic(data_engine):
    """
    Verify that auto_adjust is disabled for .TW/.TWO tickers and enabled for others.
    """
    
    # Mock return value for download (empty dataframe is fine, we just check call args)
    mock_df = pd.DataFrame()
    
    with patch('yfinance.download', return_value=mock_df) as mock_download:
        # Case 1: 0056.TW (Taiwan ETF) -> Should use auto_adjust=False
        data_engine.fetch_data("0056.TW")
        
        # Check arguments of the last call
        args, kwargs = mock_download.call_args
        assert kwargs.get('auto_adjust') is False, "0056.TW should have auto_adjust=False"
        
        # Case 2: AAPL (US Stock) -> Should use auto_adjust=True (default/explicit)
        data_engine.fetch_data("AAPL")
        
        args, kwargs = mock_download.call_args
        # The current implementation hardcodes auto_adjust=True, so this should pass currently
        # But after fix, it should still be True.
        # Wait, if I am TDDing, I should expect the FIRST assertion to FAIL.
        # Currently the code has auto_adjust=True for everything.
        assert kwargs.get('auto_adjust') is True, "AAPL should have auto_adjust=True"

        # Case 3: 6547.TWO (Taiwan OTC) -> Should use auto_adjust=False
        data_engine.fetch_data("6547.TWO")
        args, kwargs = mock_download.call_args
        assert kwargs.get('auto_adjust') is False, "6547.TWO should have auto_adjust=False"
