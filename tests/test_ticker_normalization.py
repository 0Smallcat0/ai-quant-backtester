import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from src.data_engine import DataManager

class TestTickerNormalization:
    @pytest.fixture
    def data_manager(self):
        return DataManager(db_path=":memory:")

    @patch('src.data_engine.yf.Ticker')
    def test_normalize_ticker_standard_stock(self, mock_ticker, data_manager):
        """Case A: Standard Stock (4 digits) - Should return with .TW suffix"""
        # Setup mock to return non-empty history for 2330.TW
        mock_instance = MagicMock()
        mock_instance.history.return_value = pd.DataFrame({'Close': [100]})
        mock_ticker.return_value = mock_instance

        result = data_manager.normalize_ticker("2330")
        assert result == "2330.TW"

    @patch('src.data_engine.yf.Ticker')
    def test_normalize_ticker_etf_6_digit(self, mock_ticker, data_manager):
        """Case B: ETF/Bond (6 digits) - Should return with .TW suffix"""
        # Setup mock to return non-empty history for 006208.TW
        mock_instance = MagicMock()
        mock_instance.history.return_value = pd.DataFrame({'Close': [100]})
        mock_ticker.return_value = mock_instance

        # This is expected to fail before the fix because regex only matches 4 digits
        result = data_manager.normalize_ticker("006208")
        assert result == "006208.TW"

    @patch('src.data_engine.yf.Ticker')
    def test_normalize_ticker_with_letter_suffix(self, mock_ticker, data_manager):
        """Case: Bond/Leveraged/Inverse ETFs with letter suffixes"""
        # Setup mock
        mock_instance = MagicMock()
        mock_instance.history.return_value = pd.DataFrame({'Close': [100]})
        mock_ticker.return_value = mock_instance

        # Bond ETF
        assert data_manager.normalize_ticker("00679B") == "00679B.TW"
        # Leveraged ETF
        assert data_manager.normalize_ticker("00631L") == "00631L.TW"
        # Inverse ETF
        assert data_manager.normalize_ticker("00632R") == "00632R.TW"

    def test_normalize_ticker_already_suffixed(self, data_manager):
        """Case C: Already Suffixed - Should return as is"""
        result = data_manager.normalize_ticker("006208.TW")
        assert result == "006208.TW"
