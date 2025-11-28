import ccxt
import pandas as pd
import logging
from datetime import datetime
from src.data_loader.providers.base import BaseDataProvider

logger = logging.getLogger(__name__)

class CcxtProvider(BaseDataProvider):
    """Data provider using CCXT (Binance) for Crypto."""

    def __init__(self, exchange_id: str = 'binance'):
        """
        Initialize CCXT provider.
        :param exchange_id: 'binance' or 'kraken'
        """
        self.exchange_id = exchange_id
        if exchange_id == 'binance':
            self.exchange = ccxt.binance({'enableRateLimit': True})
        elif exchange_id == 'kraken':
            self.exchange = ccxt.kraken({'enableRateLimit': True})
        else:
            raise ValueError(f"Unsupported exchange: {exchange_id}")

    def _normalize_symbol(self, ticker: str) -> str:
        """
        Convert YFinance ticker to CCXT symbol.
        Example: 'BTC-USD' -> 'BTC/USDT' (Binance) or 'BTC/USD' (Kraken)
        """
        if ticker.endswith('-USD'):
            if self.exchange_id == 'binance':
                return ticker.replace('-USD', '/USDT')
            elif self.exchange_id == 'kraken':
                return ticker.replace('-USD', '/USD')
        return ticker

    def fetch_history(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical data from Binance via CCXT.
        """
        symbol = self._normalize_symbol(ticker)
        
        # Convert dates to Unix timestamp (milliseconds)
        start_ts = int(pd.Timestamp(start_date).timestamp() * 1000)
        end_ts = int(pd.Timestamp(end_date).timestamp() * 1000)
        
        all_ohlcv = []
        current_ts = start_ts
        limit = 1000 # Binance limit
        
        while current_ts < end_ts:
            try:
                logger.info(f"Fetching {symbol} from {pd.to_datetime(current_ts, unit='ms')}...")
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe='1d', since=current_ts, limit=limit)
                
                if not ohlcv:
                    break
                
                all_ohlcv.extend(ohlcv)
                
                # Update current_ts to the last timestamp + 1 day (in ms)
                last_ts = ohlcv[-1][0]
                current_ts = last_ts + 86400000 # Add 1 day in ms
                
                # If we fetched less than limit, we probably reached the end
                if len(ohlcv) < limit:
                    break
                    
            except Exception as e:
                logger.warning(f"Error fetching {symbol} at {current_ts}: {e}")
                break
        
        if not all_ohlcv:
            raise ValueError(f"No data found for {ticker} (as {symbol}) from CCXT")
            
        # Convert to DataFrame
        # CCXT format: [timestamp, open, high, low, close, volume]
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('date')
        df = df.drop(columns=['timestamp'])
        
        # Filter by end_date (since we might have fetched a bit more)
        df = df[df.index <= pd.Timestamp(end_date)]
        df = df.sort_index()
        
        if df.empty:
             raise ValueError(f"No data found for {ticker} in range {start_date}-{end_date}")

        return df
