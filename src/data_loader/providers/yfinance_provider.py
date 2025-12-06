import yfinance as yf
import pandas as pd
from src.data_loader.providers.base import BaseDataProvider
import time
from src.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class DataFetchError(Exception):
    """Exception raised when data download Quality Checks fail."""
    pass

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

                # [CLEANUP] 1. Future Filter
                today = pd.Timestamp.now().normalize()
                df = df[df.index <= today]
                
                # [CLEANUP] 2. Tail Check (Drop last row if Volume is 0/NaN)
                if not df.empty and 'Volume' in df.columns:
                     last_vol = df['Volume'].iloc[-1]
                     if pd.isna(last_vol) or last_vol == 0:
                         logger.warning(f"Dropping last row for {ticker} ({df.index[-1]}) due to incomplete data (Vol={last_vol})")
                         df = df.iloc[:-1]

                # [CLEANUP] 3. Smart Imputation
                if 'Volume' in df.columns:
                     import numpy as np # Local import to ensure availability
                     # Replace 0 with NaN, then forward fill, then fill remaining NaNs with 0
                     df['Volume'] = df['Volume'].replace(0, np.nan).ffill().fillna(0)

                # [CRITICAL] Poison Pill Guard: Zero-Volume Anomaly Detection
                if 'Volume' in df.columns:
                    # Count zeros AND NaNs (After imputation, NaNs should be 0, but Zeros might persist if at start)
                    vol_series = df['Volume']
                    
                    bad_vol_count = (vol_series == 0) | (vol_series.isna())
                    bad_ratio = bad_vol_count.mean()
                    
                    if isinstance(bad_ratio, pd.Series):
                         bad_ratio = bad_ratio.max()
                    
                    # [STRICTER] If > 10% bad (Zero or NaN) AFTER imputation, reject.
                    # This means we couldn't impute them (e.g. data started with zeros).
                    if bad_ratio > 0.1: 
                         msg = f"CRITICAL: Data quality failed for {ticker}. Bad Volume Ratio: {bad_ratio:.2%}. Triggering Fallback."
                         logger.error(msg)
                         raise DataFetchError(msg)

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
