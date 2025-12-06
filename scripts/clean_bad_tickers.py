import sqlite3
from pathlib import Path

# Explicit path based on existing project structure
DB_PATH = Path("d:/ai-quant-backtester/data/market_data.db")

def clean_bad_data():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}. Nothing to clean.")
        return

    print(f"Connecting to database at {DB_PATH}...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        bad_tickers = ['0050.TW', '0056.TW']
        placeholders = ','.join('?' for _ in bad_tickers)

        # 1. Clean OHLCV
        query_ohlcv = f"DELETE FROM ohlcv WHERE ticker IN ({placeholders})"
        cursor.execute(query_ohlcv, bad_tickers)
        rows_ohlcv = cursor.rowcount
        print(f"Deleted {rows_ohlcv} rows from 'ohlcv' for tickers {bad_tickers}")

        # 2. Clean Metadata
        query_meta = f"DELETE FROM metadata WHERE ticker IN ({placeholders})"
        cursor.execute(query_meta, bad_tickers)
        rows_meta = cursor.rowcount
        print(f"Deleted {rows_meta} rows from 'metadata' for tickers {bad_tickers}")

        conn.commit()
        print("Cleanup committed successfully.")

    except Exception as e:
        print(f"Error during cleanup: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    clean_bad_data()
