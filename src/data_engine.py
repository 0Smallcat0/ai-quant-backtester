import sqlite3

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import time
import re
from typing import Optional, List, Callable, Any
from typing import Optional, List, Callable, Any
from src.utils import sanitize_ticker
from src.config.settings import settings
from src.data.news_engine import NewsEngine
from src.config.logging_config import setup_logging

from src.data_loader.providers.yfinance_provider import YFinanceProvider
from src.data_loader.providers.stooq_provider import StooqProvider
from src.data_loader.providers.twstock_provider import TwStockProvider
from src.data_loader.providers.ccxt_provider import CcxtProvider

logger = setup_logging(__name__)

class DataManager:
    def __init__(self, db_path: str, news_engine: Optional[Any] = None):
        self.db_path = db_path
        self.news_engine = news_engine
        self.yf_provider = YFinanceProvider()
        self.stooq_provider = StooqProvider()
        self.twstock_provider = TwStockProvider()
        self.ccxt_provider = CcxtProvider()

    def get_connection(self) -> sqlite3.Connection:
        # [SAFETY] Increased timeout to prevent 'database is locked' errors
        return sqlite3.connect(self.db_path, timeout=settings.DEFAULT_TIMEOUT)

    def init_db(self) -> None:
        """Initialize the SQLite database with required tables."""
        logger.info(f"Initializing DB at {self.db_path}")
        conn = self.get_connection()
        
        # [OPTIMIZATION] Enable WAL mode and synchronous=NORMAL for performance
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        
        cursor = conn.cursor()
        
        # OHLCV Data Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ohlcv (
                ticker TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                PRIMARY KEY (ticker, date)
            )
        ''')
        
        # Metadata Table (for tracking last update)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                ticker TEXT PRIMARY KEY,
                last_updated TEXT
            )
        ''')

        # Watchlist Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracked_symbols (
                symbol TEXT PRIMARY KEY
            )
        ''')
        
        conn.commit()
        conn.close()

    def normalize_ticker(self, ticker: str) -> str:
        """
        Normalize ticker symbol for different markets using MARKET_CONFIG.
        """
        try:
            # [FIX] Sanitize ticker
            ticker = sanitize_ticker(ticker)
            
            for market, config in settings.MARKET_CONFIG.items():
                # Check known symbols first
                known = config.get('known', set())
                if ticker in known:
                    suffixes = config.get('suffixes', [])
                    if suffixes:
                        return f"{ticker}{suffixes[0]}"
                    return ticker

                pattern = config.get('pattern')
                suffixes = config.get('suffixes', [])
                
                if re.match(pattern, ticker):
                    # If it matches the pattern, try suffixes
                    if not suffixes:
                        # If US (no suffix), we can't easily distinguish from Crypto by pattern alone
                        # unless we check existence. 
                        # But since US is before Crypto in dict (usually), it matches US first.
                        # If we want to support implicit Crypto, we rely on 'known' list.
                        return ticker
                        
                    for suffix in suffixes:
                        test_ticker = f"{ticker}{suffix}"
                        try:
                            # Fast check with history
                            hist = yf.Ticker(test_ticker).history(period='1d')
                            if not hist.empty:
                                return test_ticker
                        except:
                            pass
                    
                    # Default to first suffix if check fails but matches pattern
                    if suffixes and config.get('default_on_fail', False):
                        return f"{ticker}{suffixes[0]}"
            
            return ticker
        except Exception as e:
            logger.warning(f"Warning: normalize_ticker failed for {ticker}: {e}. Returning original.")
            return ticker

    def _calc_smart_start(self, ticker: str) -> str:
        """
        Calculate the smart start date for updating data.
        - If no data: Returns "2000-01-01"
        - If data exists: Returns last_updated + 1 day
        - If up-to-date: Returns None (indicates no update needed)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT last_updated FROM metadata WHERE ticker=?", (ticker,))
        row = cursor.fetchone()
        conn.close()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        if not row:
            return settings.DEFAULT_START_DATE
            
        last_updated = row[0]
        
        if last_updated >= today:
            return None # Up to date
            
        # If we have data, start from next day
        last_dt = pd.to_datetime(last_updated)
        next_day = last_dt + pd.Timedelta(days=1)
        start_date = next_day.strftime('%Y-%m-%d')
        
        if start_date > today:
            return None
            
        return start_date

    def fetch_data(self, ticker: str, start_date: Optional[str] = None, end_date: Optional[str] = None, progress_callback: Optional[Callable[[float, str], None]] = None) -> None:
        """
        Fetch data using providers and store in DB.
        Supports chunked downloading for progress tracking.
        """
        # [FIX] Normalize ticker to ensure correct suffix (e.g., 00679B -> 00679B.TWO)
        ticker = self.normalize_ticker(ticker)

        # Default to a reasonable start date if not provided
        if not start_date:
            start_date = settings.DEFAULT_START_DATE
        
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # Convert to datetime objects for chunking
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # Generate chunks based on MAX_CHUNK_YEARS
        year_start = start_dt.year
        year_end = end_dt.year
        
        chunk_start_years = range(year_start, year_end + 1, settings.MAX_CHUNK_YEARS)
        total_chunks = len(chunk_start_years)
        
        all_dfs = []
        
        for i, chunk_start_year in enumerate(chunk_start_years):
            chunk_end_year = min(chunk_start_year + settings.MAX_CHUNK_YEARS - 1, year_end)
            
            chunk_start = f"{chunk_start_year}-01-01"
            chunk_end = f"{chunk_end_year}-12-31"
            
            # Adjust for actual start/end
            if chunk_start_year == year_start:
                chunk_start = start_date
            if chunk_end_year == year_end:
                chunk_end = end_date
                
            # Skip if start > end
            if pd.to_datetime(chunk_start) > pd.to_datetime(chunk_end):
                continue

            if progress_callback:
                progress_callback(i / total_chunks, f"Downloading {ticker} data for {chunk_start_year}-{chunk_end_year}...")

            # Provider Failover Logic
            df_chunk = pd.DataFrame()
            try:
                # Step 1: Try YFinance
                df_chunk = self.yf_provider.fetch_history(ticker, chunk_start, chunk_end)
            except Exception as e:
                logger.warning(f"YFinance failed for {ticker} ({chunk_start} to {chunk_end}): {e}")
                
                # Step 2: Check if US stock (simple heuristic: no dot suffix, or explicit check)
                # In this system, US stocks usually don't have suffixes like .TW
                is_us_stock = '.' not in ticker
                is_tw_stock = ticker.endswith('.TW') or ticker.endswith('.TWO')
                is_crypto = ticker.endswith('-USD') and not is_tw_stock
                
                if is_tw_stock:
                    try:
                        # Step 3a: Fallback to TwStock
                        logger.warning(f"Falling back to TwStock for {ticker}...")
                        df_chunk = self.twstock_provider.fetch_history(ticker, chunk_start, chunk_end)
                    except Exception as tw_e:
                        logger.error(f"TwStock also failed for {ticker}: {tw_e}")
                elif is_crypto:
                    try:
                        # Step 3b: Fallback to CCXT
                        logger.warning(f"Falling back to CCXT for {ticker}...")
                        df_chunk = self.ccxt_provider.fetch_history(ticker, chunk_start, chunk_end)
                    except Exception as ccxt_e:
                        logger.error(f"CCXT also failed for {ticker}: {ccxt_e}")
                elif is_us_stock:
                    try:
                        # Step 3c: Fallback to Stooq
                        logger.warning(f"Falling back to Stooq for {ticker}...")
                        df_chunk = self.stooq_provider.fetch_history(ticker, chunk_start, chunk_end)
                    except Exception as stooq_e:
                        logger.error(f"Stooq also failed for {ticker}: {stooq_e}")
                else:
                    logger.error(f"No fallback available for stock {ticker}")

            if not df_chunk.empty:
                all_dfs.append(df_chunk)

        if progress_callback:
            progress_callback(1.0, f"Finalizing {ticker} data...")

        
        if not all_dfs:
            logger.warning(f"No data fetched for {ticker}")
            return

        # [ROBUSTNESS] Deduplication and Sorting
        df = pd.concat(all_dfs)
        # Ensure index is named 'date' for consistency before reset_index if possible, 
        # but better to reset first then rename.
        df.index.name = 'date' 
        df = df.reset_index()
        
        # Normalize columns to lowercase
        df.columns = [str(c).lower() for c in df.columns]
        
        # [FIX] Handle Volume NaN/Zero issues
        # Ensure 'volume' exists (renamed from 'Volume' by lowercase above)
        if 'volume' in df.columns:
            # Forward fill volume first (assume missing volume is same as previous day or 0)
            # Then fill remaining NaNs with 0
            df['volume'] = df['volume'].ffill().fillna(0).astype(float)
        
        # [ROBUSTNESS] Drop duplicates based on date
        if 'date' in df.columns:
            df = df.drop_duplicates(subset=['date']).sort_values('date')
        
        # Efficient way:
        data_tuples = []
        for _, row in df.iterrows():
            # Ensure we access the correct columns. yfinance usually gives 'Date' which becomes 'date'
            # and 'Open', 'High' etc which become 'open', 'high'
            try:
                data_tuples.append((
                    ticker, row['date'].strftime('%Y-%m-%d'), row['open'], row['high'], 
                    row['low'], row['close'], row['volume']
                ))
            except KeyError as e:
                logger.warning(f"Skipping row due to missing column: {e}")
                continue
            
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT OR REPLACE INTO ohlcv (ticker, date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', data_tuples)
        
        # Update Metadata
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            INSERT OR REPLACE INTO metadata (ticker, last_updated)
            VALUES (?, ?)
        ''', (ticker, today))
        
        conn.commit()
        conn.close()

    def save_data(self, df: pd.DataFrame, ticker: str) -> None:
        """
        Save OHLCV data to database.
        Expects DataFrame with columns: open, high, low, close, volume.
        Index should be date.
        """
        if df.empty:
            return

        # Ensure index is date
        if 'date' not in df.columns and isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
            df.rename(columns={'index': 'date'}, inplace=True)
            
        # Normalize columns
        df.columns = [str(c).lower() for c in df.columns]
        
        data_tuples = []
        for _, row in df.iterrows():
            try:
                date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                data_tuples.append((
                    ticker, date_str, row['open'], row['high'], 
                    row['low'], row['close'], row['volume']
                ))
            except KeyError as e:
                continue
                
        conn = self.get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.executemany('''
                    INSERT OR REPLACE INTO ohlcv (ticker, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', data_tuples)
                
                # Update Metadata
                today = datetime.now().strftime('%Y-%m-%d')
                cursor.execute('''
                    INSERT OR REPLACE INTO metadata (ticker, last_updated)
                    VALUES (?, ?)
                ''', (ticker, today))
        finally:
            conn.close()


    def get_data(self, ticker: str, include_sentiment: bool = False) -> pd.DataFrame:
        """Load data from DB for a specific ticker."""
        # [FIX] Sanitize ticker
        ticker = sanitize_ticker(ticker)
        conn = self.get_connection()
        try:
            # Use parameterized query for safety, though ticker is internal
            query = "SELECT * FROM ohlcv WHERE ticker=? ORDER BY date ASC"
            df = pd.read_sql(query, conn, params=(ticker,))
        finally:
            conn.close()
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date') # Explicit assignment instead of inplace
            
            # [FIX] Enforce lowercase columns (Data Management Protocol)
            # Remove TitleCase renaming and ensure all columns are lowercase
            df.columns = [c.lower() for c in df.columns]
            
            # Ensure numeric columns are floats
            cols = ['open', 'high', 'low', 'close', 'volume']
            for c in cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce')
            
            # [SAFETY] Clean Data: Smart Patching
            # 1. Replace Inf with NaN
            df = df.replace([np.inf, -np.inf], np.nan)
            
            # 2. Fix Volume (Missing volume -> 0.0)
            if 'volume' in df.columns:
                df['volume'] = df['volume'].fillna(0.0)
            
            # 3. Fix Price (Missing price -> ffill, then drop if still missing)
            price_cols = [c for c in ['open', 'high', 'low', 'close'] if c in df.columns]
            if price_cols:
                df[price_cols] = df[price_cols].ffill()
                df = df.dropna(subset=price_cols)
            else:
                # Fallback if no price columns (unlikely)
                df = df.dropna()

            # [NEW] Integrate Sentiment
            if include_sentiment:
                try:
                    # Use injected engine or lazy load
                    engine = self.news_engine if self.news_engine else NewsEngine()
                    start_date = df.index.min().strftime('%Y-%m-%d')
                    end_date = df.index.max().strftime('%Y-%m-%d')
                    
                    sentiment_series = engine.get_sentiment(ticker, start_date, end_date)
                    
                    # Merge (Left Join)
                    df = df.join(sentiment_series, how='left')
                    
                    # Fill NaNs with 0.0 (Neutral)
                    if 'sentiment' in df.columns:
                        df['sentiment'] = df['sentiment'].fillna(0.0)
                    else:
                        df['sentiment'] = 0.0
                        
                except Exception as e:
                    logger.warning(f"Warning: Failed to integrate sentiment for {ticker}: {e}")
                    df['sentiment'] = 0.0
        
        # [ROBUSTNESS] Empty Guard
        if df.empty:
            raise ValueError(f"No valid data for ticker '{ticker}' after cleaning")
                
        return df

    def update_data_if_needed(self, ticker: str, progress_callback: Optional[Callable[[float, str], None]] = None) -> None:
        """Check if data is stale and update if necessary."""
        # [REFACTOR] Use _calc_smart_start
        start_date = self._calc_smart_start(ticker)
        
        if start_date:
            logger.info(f"Updating data for {ticker} from {start_date}...")
            self.fetch_data(ticker, start_date=start_date, progress_callback=progress_callback)
        else:
            logger.info(f"Data for {ticker} is up to date.")
            if progress_callback:
                progress_callback(1.0, "Data is up to date.")

    def add_to_watchlist(self, symbol: str) -> None:
        """Add a symbol to the watchlist."""
        if not symbol or not symbol.strip():
            raise ValueError("Ticker symbol cannot be empty.")
        # [FIX] Sanitize symbol
        symbol = sanitize_ticker(symbol)
        
        # [FIX] Normalize symbol (e.g., 00679B -> 00679B.TWO)
        symbol = self.normalize_ticker(symbol)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT OR IGNORE INTO tracked_symbols (symbol) VALUES (?)", (symbol,))
            conn.commit()
        finally:
            conn.close()

    def remove_from_watchlist(self, symbol: str) -> None:
        """Remove a symbol from the watchlist."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM tracked_symbols WHERE symbol=?", (symbol,))
            conn.commit()
        finally:
            conn.close()

    def get_watchlist(self) -> List[str]:
        """Get all symbols from the watchlist."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT symbol FROM tracked_symbols")
            rows = cursor.fetchall()
            return [row[0] for row in rows]
        finally:
            conn.close()

    def update_all_tracked_symbols(self, progress_callback: Optional[Callable[[float, str], None]] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> None:
        """
        Update all symbols in the watchlist.
        Smart logic:
        - If no data: Download from 2000-01-01.
        - If data exists: Download from last_updated + 1 day.
        - If up-to-date: Skip.
        
        Overrides:
        - If start_date is provided, it overrides the smart start date logic.
        - If end_date is provided, it overrides the default end date (today).
        """
        watchlist = self.get_watchlist()
        if not watchlist:
            logger.info("Watchlist is empty.")
            return
        
        total = len(watchlist)
        
        for i, symbol in enumerate(watchlist):
            if progress_callback:
                progress_callback(i / total, f"Checking {symbol} ({i+1}/{total})...")
            
            logger.info(f"Processing {symbol}...")
            
            current_start_date = start_date
            current_end_date = end_date
            
            # If no start_date override, use smart logic
            if not current_start_date:
                # [REFACTOR] Use _calc_smart_start
                smart_start = self._calc_smart_start(symbol)
                if not smart_start:
                    logger.info(f"{symbol} is up-to-date.")
                    continue
                current_start_date = smart_start

            logger.info(f"Updating {symbol} from {current_start_date}...")
            self.fetch_data(symbol, start_date=current_start_date, end_date=current_end_date, progress_callback=None) # Internal progress handled?
            
            # Sleep to avoid rate limit
            time.sleep(settings.RATE_LIMIT_SLEEP)

        if progress_callback:
            progress_callback(1.0, "All symbols updated.")
