
import os
import shutil
import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from src.data.news_engine import NewsEngine

# Mock data
TEST_TICKER = "TEST_SMART"
CACHE_DIR = "tests/temp_cache"

@pytest.fixture
def news_engine():
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)
    os.makedirs(CACHE_DIR)
    
    # Mock components to avoid real API calls
    mock_fetcher = MagicMock()
    mock_analyzer = MagicMock()
    mock_decay = MagicMock()
    
    engine = NewsEngine(
        cache_dir=CACHE_DIR,
        fetcher=mock_fetcher,
        analyzer=mock_analyzer,
        decay_model=mock_decay
    )
    yield engine
    
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)

def test_smart_update_skip_recent(news_engine):
    """
    Case 1: File modified recently (Logic: Today - last_updated < threshold) -> SKIP
    """
    # 1. Create a dummy parquet file with recent modification time
    cache_path = os.path.join(CACHE_DIR, f"{TEST_TICKER}.parquet")
    df = pd.DataFrame({'sentiment': [0.5]}, index=pd.to_datetime(['2024-01-01']))
    df.to_parquet(cache_path)
    
    # Set mtime to NOW (Very recent)
    now = datetime.now().timestamp()
    os.utime(cache_path, (now, now))
    
    # 2. Call update_cache_smart with threshold=3 days
    # We expect fetch_headlines NOT to be called
    news_engine.update_cache_smart(TEST_TICKER, days_threshold=3)
    
    news_engine.fetcher.fetch_headlines.assert_not_called()

def test_smart_update_trigger_old(news_engine):
    """
    Case 2: File modified long ago (Logic: Today - last_updated > threshold) -> FETCH
    """
    # 1. Create a dummy parquet file
    cache_path = os.path.join(CACHE_DIR, f"{TEST_TICKER}.parquet")
    df = pd.DataFrame({'sentiment': [0.5]}, index=pd.to_datetime(['2024-01-01']))
    df.to_parquet(cache_path)
    
    # Set mtime to 5 days ago
    five_days_ago = (datetime.now() - timedelta(days=5)).timestamp()
    os.utime(cache_path, (five_days_ago, five_days_ago))
    
    # Mock fetcher to return something so process doesn't fail
    news_engine.fetcher.fetch_headlines.return_value = []
    
    # 2. Call update_cache_smart
    news_engine.update_cache_smart(TEST_TICKER, days_threshold=3)
    
    # 3. Verify fetch_headlines WAS called
    news_engine.fetcher.fetch_headlines.assert_called_once()

def test_smart_update_no_file(news_engine):
    """
    Case 3: No file exists -> FETCH
    """
    news_engine.fetcher.fetch_headlines.return_value = []
    news_engine.update_cache_smart(TEST_TICKER, days_threshold=3)
    news_engine.fetcher.fetch_headlines.assert_called_once()
