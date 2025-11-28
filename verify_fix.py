from src.data_engine import DataManager
from unittest.mock import MagicMock, patch
import pandas as pd
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("src.data_engine")
logger.setLevel(logging.INFO)

def verify_fix():
    print("Verifying fix for 00679B...")
    
    # Use temporary DB
    dm = DataManager(db_path=":memory:")
    dm.init_db()
    
    # Mock providers to avoid network calls and control behavior
    with patch.object(dm.yf_provider, 'fetch_history') as mock_yf, \
         patch.object(dm.twstock_provider, 'fetch_history') as mock_tw, \
         patch.object(dm.stooq_provider, 'fetch_history') as mock_stooq:
        
        # Setup mocks
        mock_yf.side_effect = Exception("YF Failed") # Simulate YF failure
        mock_tw.return_value = pd.DataFrame() # Simulate TwStock (empty or not, just checking call)
        
        # Action: Fetch data for un-normalized ticker
        print("Calling fetch_data('00679B')...")
        dm.fetch_data("00679B", "2023-01-01", "2023-01-05")
        
        # Verification
        # 1. Check if YFinance was called with NORMALIZED ticker
        if mock_yf.called:
            args, _ = mock_yf.call_args
            called_ticker = args[0]
            print(f"YFinance called with: {called_ticker}")
            if called_ticker == "00679B.TWO":
                print("SUCCESS: Ticker was normalized before YFinance call.")
            else:
                print(f"FAIL: Ticker was NOT normalized correctly. Got: {called_ticker}")
        else:
            print("FAIL: YFinance was not called.")

        # 2. Check Failover Logic
        # If normalized to .TWO, it should fallback to TwStock, NOT Stooq
        if mock_tw.called:
            print("SUCCESS: Fell back to TwStockProvider.")
        else:
            print("FAIL: Did NOT fall back to TwStockProvider.")
            
        if mock_stooq.called:
            print("FAIL: Incorrectly fell back to StooqProvider (US logic).")
        else:
            print("SUCCESS: Did not fall back to StooqProvider.")

if __name__ == "__main__":
    verify_fix()
