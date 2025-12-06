import twstock
import pandas as pd
import time
from src.data_loader.providers.base import BaseDataProvider
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TwStockProvider(BaseDataProvider):
    """Data provider using twstock for Taiwan stocks."""

    def _parse_ticker(self, ticker: str) -> str:
        """
        Remove .TW or .TWO suffix to get the stock code.
        Example: '2330.TW' -> '2330'
        """
        return ticker.split('.')[0]

    def fetch_history(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical data from TwStock.
        """
        stock_code = self._parse_ticker(ticker)
        stock = twstock.Stock(stock_code)
        
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # twstock fetch_from uses year, month
        # We need to fetch month by month
        
        data_list = []
        
        # Generate list of (year, month) tuples
        current = start_dt.replace(day=1)
        while current <= end_dt:
            try:
                logger.info(f"Fetching {stock_code} for {current.year}-{current.month} via twstock...")
                fetched = stock.fetch_from(current.year, current.month)
                data_list.extend(fetched)
                
                # Rate limiting to avoid ban
                time.sleep(3)
                
            except Exception as e:
                logger.warning(f"Error fetching {stock_code} for {current.year}-{current.month}: {e}")
            
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
                
        if not data_list:
            raise ValueError(f"No data found for {ticker} from TwStock")

        # Convert to DataFrame
        # twstock returns named tuples or objects, usually with attributes like date, open, high, low, close, capacity, turnover, transaction
        # Let's inspect the first item or assume standard structure
        # Standard twstock data attributes: date, capacity, turnover, open, high, low, close, change, transaction
        
        # Convert to DataFrame
        # twstock returns named tuples or objects. We should explicitly extract fields to be safe.
        processed_data = []
        for item in data_list:
            processed_data.append({
                'date': item.date,
                'open': item.open,
                'high': item.high,
                'low': item.low,
                'close': item.close,
                'capacity': item.capacity
            })
            
        df = pd.DataFrame(processed_data)
        
        # Filter by date range
        df['date'] = pd.to_datetime(df['date'])
        df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
        
        if df.empty:
             raise ValueError(f"No data found for {ticker} in range {start_date}-{end_date}")

        df = df.set_index('date')
        df = df.sort_index()
        
        # Rename columns
        df = df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'capacity': 'Volume' # twstock capacity is volume (shares traded)
        })
        
        # Ensure numeric
        cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for c in cols:
            df[c] = pd.to_numeric(df[c], errors='coerce').astype(float)
            
        return df[cols]
