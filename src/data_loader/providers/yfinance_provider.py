import yfinance as yf
import pandas as pd
from src.data_loader.providers.base import BaseDataProvider
import time
from src.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class YFinanceProvider(BaseDataProvider):
    """Data provider using yfinance."""

    def fetch_history(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical data from Yahoo Finance.
        """
        max_retries = settings.MAX_RETRIES
        
        for attempt in range(max_retries):
            try:
                # [FIX] Disable auto_adjust for Taiwan stocks to prevent zero volume bug
                use_auto_adjust = True
                if ticker.endswith('.TW') or ticker.endswith('.TWO'):
                    use_auto_adjust = False
                
                df = yf.download(ticker, start=start_date, end=end_date, progress=False, multi_level_index=False, auto_adjust=use_auto_adjust)
                
                if df.empty:
                    raise ValueError(f"No data found for {ticker} from {start_date} to {end_date}")
                
                # Normalize columns
                df.columns = [str(c).capitalize() for c in df.columns]
                df = df.sort_index()
                
                # Ensure required columns exist
                required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                if not all(col in df.columns for col in required_cols):
                     # Try to map if case differs or missing
                     # yfinance usually returns Open, High, Low, Close, Volume
                     pass

                return df[required_cols]

            except Exception as e:
                if attempt < max_retries - 1:
                    sleep_time = settings.RETRY_BACKOFF_FACTOR ** attempt
                    logger.warning(f"YFinance error for {ticker}: {e}. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"YFinance failed for {ticker} after {max_retries} attempts: {e}")
                    raise e
        return pd.DataFrame()
