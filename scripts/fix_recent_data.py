from src.data_engine import DataManager
from src.config.settings import settings
import logging
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_recent_data():
    dm = DataManager(str(settings.DB_PATH))
    tickers = ["0050.TW", "0056.TW"]
    
    conn = dm.get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Delete last 5 days
        logger.info("Step 1: Deleting last 5 days of data...")
        cutoff_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        
        for ticker in tickers:
            logger.info(f"Cleaning {ticker} after {cutoff_date}...")
            cursor.execute("DELETE FROM ohlcv WHERE ticker=? AND date >= ?", (ticker, cutoff_date))
            deleted = cursor.rowcount
            logger.info(f"Deleted {deleted} rows for {ticker}.")
            
            # Reset metadata to force update check
            # We can set last_updated to cutoff_date so it re-fetches from there
            cursor.execute("UPDATE metadata SET last_updated=? WHERE ticker=?", (cutoff_date, ticker))
        
        conn.commit()
    except Exception as e:
        logger.error(f"Error cleaning DB: {e}")
        conn.rollback()
        return
    finally:
        conn.close()

    # 2. Update Data
    logger.info("Step 2: Updating data with new logic...")
    for ticker in tickers:
        logger.info(f"Updating {ticker}...")
        # INCREMENTAL mode will see last_updated is old and fetch recent days
        # The new fetch logic in yfinance_provider will apply Imputation/Filtering
        dm.update_data_if_needed(ticker, update_mode="INCREMENTAL")
        
    logger.info("Fix complete.")

if __name__ == "__main__":
    fix_recent_data()
