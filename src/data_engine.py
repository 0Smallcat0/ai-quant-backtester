import sqlite3
import concurrent.futures
import threading


import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import time
import re
from typing import Optional, List, Callable, Any
from typing import Optional, List, Callable, Any
from src.utils import sanitize_ticker, detect_market
import src.utils
from src.config.settings import settings
from src.data.news_engine import NewsEngine
from src.config.logging_config import setup_logging
import shutil
import os

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
        self._local = threading.local()

    # [PERFORMANCE] Thread-Local Storage for Connection Pooling


    def get_connection(self) -> sqlite3.Connection:
        """
        Get a thread-local database connection.
        If a connection exists for this thread, reuse it.
        Otherwise, create a new one.
        """
        # Check if we have a cached connection
        conn = getattr(self._local, 'conn', None)
        
        is_closed = True
        if conn:
            try:
                # Check if connection is valid by running a lightweight query
                conn.execute("SELECT 1").close()
                is_closed = False
            except (sqlite3.ProgrammingError, sqlite3.InterfaceError):
                # Connection is closed or invalid
                is_closed = True
            except Exception as e:
                logger.warning(f"Unexpected error checking DB connection: {e}. Recreating.")
                is_closed = True
        
        if is_closed:
            # Create new connection for this thread
            self._local.conn = sqlite3.connect(self.db_path, timeout=settings.DEFAULT_TIMEOUT)
            # [OPTIMIZATION] Enable WAL mode for every new connection
            self._local.conn.execute("PRAGMA journal_mode=WAL;")
            self._local.conn.execute("PRAGMA synchronous=NORMAL;")
            
        return self._local.conn

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
        
        # [OPTIMIZATION] Index for faster range queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker_date ON ohlcv (ticker, date);
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
            ticker = src.utils.sanitize_ticker(ticker)
            
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
                    # [HOTFIX] Protection against US stocks being treated as Crypto
                    # If this is CRYPTO market, and ticker is short (len<=5) and NOT known, skip it.
                    # This prevents NVDA -> NVDA-USD.
                    if market == 'CRYPTO' and len(ticker) <= 5 and ticker not in known:
                        continue

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
        
        # [OPTIMIZATION] Sticky Provider Logic: Start with Primary
        current_provider = self.yf_provider

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
                # Step 1: Try Current Sticky Provider
                df_chunk = current_provider.fetch_history(ticker, chunk_start, chunk_end)
            except Exception as e:
                provider_name = type(current_provider).__name__
                logger.warning(f"{provider_name} failed for {ticker} ({chunk_start} to {chunk_end}): {e}")
                
                # If we are currently on Primary (YFinance), try to switch to Backup
                if current_provider == self.yf_provider:
                    backup = self._get_backup_provider(ticker)
                    if backup:
                        logger.warning(f"Switching to Backup Provider ({type(backup).__name__})...")
                        current_provider = backup # [STICKY] Permanently switch for this session
                        
                        try:
                            # Immediate Retry with New Provider
                            df_chunk = current_provider.fetch_history(ticker, chunk_start, chunk_end)
                        except Exception as e_backup:
                            logger.error(f"Backup {type(current_provider).__name__} also failed: {e_backup}")
                    else:
                        logger.error(f"No backup provider found for {ticker}")
                else:
                    # We were already on backup and it failed
                    logger.error(f"Backup provider {provider_name} failed. No further fallback.")

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
                
                # Update Metadata ONLY if we actually processed data
                if len(data_tuples) > 0:
                    today = datetime.now().strftime('%Y-%m-%d')
                    cursor.execute('''
                        INSERT OR REPLACE INTO metadata (ticker, last_updated)
                        VALUES (?, ?)
                    ''', (ticker, today))
        finally:
            conn.close()


    def get_data(self, ticker: str, include_sentiment: bool = False, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """Load data from DB for a specific ticker with optional date range filtering."""
        # [FIX] Sanitize ticker
        ticker = sanitize_ticker(ticker)
        
        # Default dates for SQL query range
        # Use simple string comparison for dates as they are ISO8601 YYYY-MM-DD
        sql_start = start_date if start_date else "1900-01-01"
        sql_end = end_date if end_date else "2099-12-31"

        conn = self.get_connection()
        try:
            # [OPTIMIZATION] SQL Range Query instead of loading full history
            query = "SELECT * FROM ohlcv WHERE ticker=? AND date >= ? AND date <= ? ORDER BY date ASC"
            df = pd.read_sql(query, conn, params=(ticker, sql_start, sql_end))
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

    def _get_backup_provider(self, ticker: str) -> Optional[Any]:
        """
        Get the appropriate backup provider for a ticker.
        """
        market = detect_market(ticker)
        if market == 'TW':
            return self.twstock_provider
        elif market == 'CRYPTO':
            return self.ccxt_provider
        else:
            # Assume US stock or Other
            return self.stooq_provider

    def update_data_if_needed(self, ticker: str, progress_callback: Optional[Callable[[float, str], None]] = None, update_mode: Optional[str] = None, start_date: Optional[str] = None) -> None:
        """Check if data is stale and update if necessary."""
        
        mode = update_mode if update_mode else settings.DATA_UPDATE_MODE
        calc_start = self._calc_smart_start(ticker)
        
        # Determine Final Start Date
        final_start = None
        
        if mode == "INCREMENTAL":
            # Smart Start Logic
            # Priority: User Input > Calculated Start
            if start_date:
                # If no data exists (calc_start == 2000), use user input.
                if calc_start == settings.DEFAULT_START_DATE:
                    final_start = start_date
                else:
                    # We have some data.
                    # For INCREMENTAL, we generally want to fill gaps or extend.
                    # If user says 2020 but we have valid data until 2023, usage of max(2020, 2024ish)
                    # protects against re-downloading.
                    if calc_start is None:
                        # Data is up to date relative to TODAY.
                        logger.info(f"Data for {ticker} seems up to date (Calculated). ignoring user input {start_date} for INCREMENTAL safety.")
                        final_start = None
                    else:
                        # Use the later date to avoid re-downloading overlap if not needed
                        # BUT if user wants to fill a gap *before* existing data, INCREMENTAL isn't the right mode.
                        # Assuming standard forward-fill usage:
                        final_start = max(start_date, calc_start)
            else:
                 final_start = calc_start
            
            logger.info(f"Update Strategy: {mode}, User Start: {start_date}, Calculated: {calc_start}, Final: {final_start}")
            
            if final_start:
                logger.info(f"Updating data for {ticker} from {final_start}...")
                self.fetch_data(ticker, start_date=final_start, progress_callback=progress_callback)
            else:
                logger.info(f"Data for {ticker} is up to date.")
                if progress_callback:
                    progress_callback(1.0, "Data is up to date.")
                    
        elif mode == "FULL_VERIFY":
            logger.info(f"Running FULL VERIFICATION for {ticker}...")
            
            # Step 1: Fetch Full History from Primary (YFinance)
            # [FIX] Respect User Start Date if provided, otherwise default to 2000
            verify_start_date = start_date if start_date else "2000-01-01"
            
            logger.info(f"Update Strategy: {mode}, User Start: {start_date}, Verify Start: {verify_start_date}")
            
            try:
                # Use verify_start_date instead of hardcoded 2000-01-01
                df_new_pri = self.yf_provider.fetch_history(ticker, verify_start_date, datetime.now().strftime('%Y-%m-%d'))
            except Exception as e:
                logger.error(f"Primary provider failed for {ticker}: {e}")
                return

            if df_new_pri.empty:
                logger.warning(f"Primary provider returned empty data for {ticker}")
                return
                
            # Normalize columns
            df_new_pri.columns = [str(c).lower() for c in df_new_pri.columns]
            df_new_pri.index.name = 'date'
            
            # Step 2: Load Old Data
            try:
                df_old = self.get_data(ticker)
            except ValueError:
                # No old data, just save new data
                logger.info(f"No existing data for {ticker}. Saving new data.")
                self.save_data(df_new_pri, ticker)
                return

            # Step 3: Compare
            # Align indices
            common_dates = df_old.index.intersection(df_new_pri.index)
            
            if common_dates.empty:
                logger.info(f"No overlapping dates for {ticker}. Appending new data.")
                self.save_data(df_new_pri, ticker)
                return
                
            df_old_common = df_old.loc[common_dates]
            df_new_pri_common = df_new_pri.loc[common_dates]
            
            # Check for differences
            # We focus on OHLCV
            cols_to_check = ['open', 'high', 'low', 'close', 'volume']
            # Ensure columns exist
            cols_to_check = [c for c in cols_to_check if c in df_old_common.columns and c in df_new_pri_common.columns]
            
            is_diff = False
            try:
                # Use numpy isclose for float comparison
                # We need to handle NaNs carefully, but get_data cleans them.
                # However, volume might be 0 vs NaN.
                
                # Simple check: absolute difference > tolerance
                diff = (df_old_common[cols_to_check] - df_new_pri_common[cols_to_check]).abs()
                if (diff > settings.DATA_DIFF_TOLERANCE).any().any():
                    is_diff = True
            except Exception as e:
                logger.warning(f"Error comparing data: {e}. Assuming difference.")
                is_diff = True
                
            if not is_diff:
                logger.info(f"Data verification passed for {ticker}. Appending new data if any.")
                # Save the whole new dataframe (it includes new dates)
                # save_data uses INSERT OR REPLACE, so it's safe
                self.save_data(df_new_pri, ticker)
                return
                
            # Step 5: Conflict Resolution (Voting)
            logger.warning(f"Data conflict detected for {ticker}. Initiating Voting...")
            
            backup_provider = self._get_backup_provider(ticker)
            try:
                df_new_bak = backup_provider.fetch_history(ticker, "2000-01-01", datetime.now().strftime('%Y-%m-%d'))
                df_new_bak.columns = [str(c).lower() for c in df_new_bak.columns]
                df_new_bak.index.name = 'date'
            except Exception as e:
                logger.error(f"Backup provider failed for {ticker}: {e}. Keeping old data where conflict exists.")
                # We can still update new dates? 
                # For safety, let's just abort update for conflicting rows and only add new rows?
                # The requirement says "Keep Old" if backup fails (implied by Case D or inability to vote).
                return

            # Voting Logic
            # We iterate over conflicting rows or just all common rows?
            # Iterating all common rows is safer but slower.
            # Let's iterate over rows where diff > tolerance
            
            # Re-calculate diff mask
            # Align all three
            common_dates_3 = common_dates.intersection(df_new_bak.index)
            
            fixed_count = 0
            unresolved_count = 0
            
            # Prepare a list of updates
            updates = []
            
            for date in common_dates_3:
                row_old = df_old.loc[date]
                row_pri = df_new_pri.loc[date]
                row_bak = df_new_bak.loc[date]
                
                # Check if this row has conflict
                row_diff = False
                for col in cols_to_check:
                    if abs(row_old[col] - row_pri[col]) > settings.DATA_DIFF_TOLERANCE:
                        row_diff = True
                        break
                
                if not row_diff:
                    continue
                    
                # Voting
                # Case A: New_Pri == New_Bak -> Update DB
                pri_eq_bak = True
                for col in cols_to_check:
                    if abs(row_pri[col] - row_bak[col]) > settings.DATA_DIFF_TOLERANCE:
                        pri_eq_bak = False
                        break
                
                if pri_eq_bak:
                    # Update DB with New_Pri
                    updates.append(row_pri)
                    fixed_count += 1
                    continue
                    
                # Case B: New_Pri == Old -> Keep Old (Already in DB)
                # Case C: New_Bak == Old -> Keep Old (Already in DB)
                # Case D: All different -> Keep Old
                
                # We only need to act if we want to change DB.
                # Since DB has Old, we only act in Case A.
                
                # But we should log unresolved
                # Check if it's Case B or C to distinguish from D
                pri_eq_old = True
                for col in cols_to_check:
                    if abs(row_pri[col] - row_old[col]) > settings.DATA_DIFF_TOLERANCE:
                        pri_eq_old = False
                        break
                        
                bak_eq_old = True
                for col in cols_to_check:
                    if abs(row_bak[col] - row_old[col]) > settings.DATA_DIFF_TOLERANCE:
                        bak_eq_old = False
                        break
                        
                if not pri_eq_old and not bak_eq_old:
                    # Case D
                    logger.error(f"Data Conflict Unresolved for {ticker} on {date}")
                    unresolved_count += 1
            
            # Apply updates
            if updates:
                df_updates = pd.DataFrame(updates)
                # [FIX] Restore index from Series names (dates)
                df_updates.index = [s.name for s in updates]
                df_updates.index.name = 'date'
                
                self.save_data(df_updates, ticker)
                
            # Also append completely new data (dates not in old)
            new_dates = df_new_pri.index.difference(df_old.index)
            if not new_dates.empty:
                df_new_only = df_new_pri.loc[new_dates]
                self.save_data(df_new_only, ticker)
                
            print(f"Verified {ticker}: {fixed_count} rows corrected, {unresolved_count} unresolved.")
            logger.info(f"Verified {ticker}: {fixed_count} rows corrected, {unresolved_count} unresolved.")

    def purge_ticker_data(self, ticker: str) -> None:
        """Purge all OHLCV and Metadata for a specific ticker."""
        # [FIX] Sanitize ticker
        ticker = sanitize_ticker(ticker)
        # [FIX] Normalize ticker
        ticker = self.normalize_ticker(ticker)
        
        logger.warning(f"Purging all data for {ticker}...")
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            with conn: # Transaction
                cursor.execute("DELETE FROM ohlcv WHERE ticker=?", (ticker,))
                rows_ohlcv = cursor.rowcount
                cursor.execute("DELETE FROM metadata WHERE ticker=?", (ticker,))
                rows_meta = cursor.rowcount
                logger.info(f"Purged {rows_ohlcv} OHLCV rows and {rows_meta} metadata rows for {ticker}.")
        except Exception as e:
            logger.error(f"Failed to purge data for {ticker}: {e}")
            raise e
        finally:
            conn.close()

    def hard_reset(self) -> None:
        """
        Hard Reset:
        1. Close DB connection (self.get_connection returns new one, but allow garbage collection).
        2. Delete SQLite DB file.
        3. Clear Sentiment Cache directory.
        4. Re-initialize DB.
        """
        logger.critical("Initiating HARD RESET. Deleting all data...")
        
        # 1. Delete DB File
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
                logger.info(f"Deleted database file: {self.db_path}")
            except Exception as e:
                logger.error(f"Failed to delete database file: {e}")
        
        # 2. Clear Sentiment Cache
        # We need the path. It's usually in self.news_engine.cache_dir if instantiated,
        # otherwise we assume default location relative to src or config?
        # DataManager doesn't strict depend on NewsEngine, but it's passed in __init__.
        # If news_engine is None, we need a fallback path or just skip.
        # But Requirement says: "src/data/sentiment_cache/"
        
        # Let's try to infer from news_engine first, or use default 'data/sentiment_cache'
        # [FIX] Use Absolute Path from Settings
        cache_dir = settings.DATA_DIR / "sentiment_cache"
        if self.news_engine and hasattr(self.news_engine, 'cache_dir'):
             # If news engine has a specific overridden path, use it, but ensure it's absolute if needed.
             # Ideally we stick to standard structure.
             pass
            
        # Ensure path is absolute or correct relative to CWD
        # CWD in user info is d:\ai-quant-backtester
        # We should use absolute path if possible, but standard is relative to project root.
        
        if os.path.exists(cache_dir):
            try:
                # Remove all files inside, but keep dir? Or remove dir and recreate?
                # Requirement: "刪除 src/data/sentiment_cache/ 目錄下的所有檔案 (保留目錄本身)"
                for filename in os.listdir(cache_dir):
                    file_path = os.path.join(cache_dir, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}. Reason: {e}")
                logger.info(f"Cleared sentiment cache at {cache_dir}")
            except Exception as e:
                logger.error(f"Failed to clear sentiment cache: {e}")
        else:
             logger.warning(f"Sentiment cache directory not found at {cache_dir}, skipping.")

        # 3. Re-init DB
        self.init_db()
        logger.info("Database re-initialized. Hard reset complete.")


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

    def update_all_tracked_symbols(self, progress_callback: Optional[Callable[[float, str], None]] = None, start_date: Optional[str] = None, end_date: Optional[str] = None, update_mode: Optional[str] = None) -> None:
        """
        Update all symbols in the watchlist using Parallel Execution.
        """
        watchlist = self.get_watchlist()
        if not watchlist:
            logger.info("Watchlist is empty.")
            return
        
        total = len(watchlist)
        completed = 0
        
        # Helper function for single ticker update to be run in thread
        def _update_single_ticker(symbol: str):
            try:
                # Local logging for thread
                # Calculate start date
                current_start_date = start_date
                
                if not current_start_date:
                    smart_start = self._calc_smart_start(symbol)
                    if not smart_start:
                        return f"{symbol} is up-to-date."
                    current_start_date = smart_start
                
                # Determine mode
                current_mode = update_mode if update_mode else settings.DATA_UPDATE_MODE
                
                # Trigger update
                # Note: We can reuse update_data_if_needed logic or call fetch_data directly.
                # Since we calculated start_date, let's call fetch_data directly to avoid re-calc
                # BUT logic in `update_data_if_needed` handles FULL_VERIFY vs INCREMENTAL.
                # Let's delegate to `update_data_if_needed` but pass `update_mode` explicitly.
                # However, `update_data_if_needed` does its own `_calc_smart_start` inside for INCREMENTAL.
                # To avoid double calc, we can just let it handle it.
                
                self.update_data_if_needed(symbol, progress_callback=None, update_mode=current_mode, start_date=current_start_date)
                return f"Updated {symbol}"
            except Exception as e:
                logger.error(f"Error updating {symbol}: {e}")
                return f"Error {symbol}: {str(e)}"

        # [OPTIMIZATION] Parallel Execution
        logger.info(f"Starting parallel update for {total} symbols with max_workers=5...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all tasks
            future_to_symbol = {executor.submit(_update_single_ticker, symbol): symbol for symbol in watchlist}
            
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    logger.info(result)
                except Exception as exc:
                    logger.error(f'{symbol} generated an exception: {exc}')
                
                completed += 1
                if progress_callback:
                    progress_callback(completed / total, f"Updated ({completed}/{total}): {symbol}")
        
        logger.info("Parallel update complete.")

