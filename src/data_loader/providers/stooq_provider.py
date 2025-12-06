import pandas_datareader.data as web
import pandas as pd
from src.data_loader.providers.base import BaseDataProvider
import logging

logger = logging.getLogger(__name__)

class StooqProvider(BaseDataProvider):
    """Data provider using Stooq via pandas-datareader."""

    def fetch_history(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical data from Stooq.
        """
        try:
            # Stooq uses 'stooq' as source
            df = web.DataReader(ticker, 'stooq', start=start_date, end=end_date)
            
            if df.empty:
                raise ValueError(f"No data found for {ticker} from Stooq")
            
            # Stooq returns data in descending order usually
            df = df.sort_index(ascending=True)
            
            # Normalize columns to Capitalized (Open, High, Low, Close, Volume)
            # Stooq usually returns: Open, High, Low, Close, Volume (already capitalized often, but let's ensure)
            df.columns = [c.capitalize() for c in df.columns]
            
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            
            # Check if all required columns are present
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing columns from Stooq data: {missing_cols}")
                
            return df[required_cols]
            
        except Exception as e:
            logger.warning(f"Stooq fetch failed for {ticker}: {e}")
            raise e
