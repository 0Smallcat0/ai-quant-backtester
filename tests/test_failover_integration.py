import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.data_engine import DataManager
import logging

class TestFailoverIntegration:
    
    @pytest.fixture
    def dm(self, tmp_path):
        # Use a temporary file instead of :memory: to ensure persistence across connections
        db_file = tmp_path / "test_db.sqlite"
        dm = DataManager(db_path=str(db_file))
        dm.init_db()
        return dm

    def test_failover_us_stock(self, dm, caplog):
        """
        Scenario A: US Failover (YFinance -> Stooq)
        Target: AAPL
        """
        caplog.set_level(logging.WARNING)
        
        # Mock YFinance to fail
        with patch.object(dm.yf_provider, 'fetch_history', side_effect=Exception("YF Connection Refused")) as mock_yf, \
             patch.object(dm.stooq_provider, 'fetch_history') as mock_stooq:
            
            # Setup Stooq mock return
            # StooqProvider returns capitalized columns and sorted index
            mock_stooq.return_value = pd.DataFrame({
                'Open': [150.0], 'High': [155.0], 'Low': [149.0], 'Close': [152.0], 'Volume': [1000.0]
            }, index=pd.to_datetime(['2023-01-03'])) # Use a weekday to avoid empty data issues if any logic checks that
            
            # Action: Fetch data (triggering failover and DB write)
            dm.fetch_data("AAPL", "2023-01-01", "2023-01-05")
            
            # Assertion 1: Failover occurred
            assert mock_yf.called
            assert mock_stooq.called
            assert "Falling back to Stooq" in caplog.text
            
            # Assertion 2: Data was written to DB and can be retrieved
            df = dm.get_data("AAPL")
            assert not df.empty
            assert len(df) == 1
            assert df.iloc[0]['close'] == 152.0

    def test_failover_tw_stock(self, dm, caplog):
        """
        Scenario B: TW Failover (YFinance -> TwStock)
        Target: 2330.TW
        """
        caplog.set_level(logging.WARNING)
        
        with patch.object(dm.yf_provider, 'fetch_history', side_effect=Exception("YF Error")) as mock_yf, \
             patch.object(dm.twstock_provider, 'fetch_history') as mock_tw:
            
            mock_tw.return_value = pd.DataFrame({
                'Open': [500.0], 'High': [510.0], 'Low': [495.0], 'Close': [505.0], 'Volume': [2000.0]
            }, index=pd.to_datetime(['2023-01-03']))
            
            dm.fetch_data("2330.TW", "2023-01-01", "2023-01-05")
            
            assert mock_yf.called
            assert mock_tw.called
            assert "Falling back to TwStock" in caplog.text
            
            df = dm.get_data("2330.TW")
            assert not df.empty
            assert df.iloc[0]['close'] == 505.0

    def test_failover_crypto(self, dm, caplog):
        """
        Scenario C: Crypto Failover (YFinance -> CCXT)
        Target: BTC-USD
        """
        caplog.set_level(logging.WARNING)
        
        with patch.object(dm.yf_provider, 'fetch_history', side_effect=Exception("YF Error")) as mock_yf, \
             patch.object(dm.ccxt_provider, 'fetch_history') as mock_ccxt:
            
            mock_ccxt.return_value = pd.DataFrame({
                'Open': [30000.0], 'High': [31000.0], 'Low': [29000.0], 'Close': [30500.0], 'Volume': [100.0]
            }, index=pd.to_datetime(['2023-01-03']))
            
            dm.fetch_data("BTC-USD", "2023-01-01", "2023-01-05")
            
            assert mock_yf.called
            assert mock_ccxt.called
            assert "Falling back to CCXT" in caplog.text
            
            df = dm.get_data("BTC-USD")
            assert not df.empty
            assert df.iloc[0]['close'] == 30500.0
