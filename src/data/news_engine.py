import os
import pandas as pd
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.data.news_fetcher import NewsFetcher
from src.data.sentiment_processor import SentimentAnalyzer, DecayModel

class NewsEngine:
    """
    Orchestrates news fetching, sentiment analysis, and caching.
    """
    def __init__(self, 
                 cache_dir: str = "data/sentiment_cache",
                 fetcher: Optional[NewsFetcher] = None,
                 analyzer: Optional[SentimentAnalyzer] = None,
                 decay_model: Optional[DecayModel] = None):
        
        self.cache_dir = cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
        self.fetcher = fetcher if fetcher else NewsFetcher()
        self.analyzer = analyzer if analyzer else SentimentAnalyzer()
        self.decay_model = decay_model if decay_model else DecayModel()
        self.logger = logging.getLogger(__name__)

    def _get_cache_path(self, ticker: str) -> str:
        # Use Parquet for better performance
        return os.path.join(self.cache_dir, f"{ticker}.parquet")

    def get_sentiment(self, ticker: str, start_date: str, end_date: str) -> pd.Series:
        """
        Get sentiment series for a ticker.
        Uses local cache if available and covers the range.
        Otherwise fetches new data.
        """
        cache_path = self._get_cache_path(ticker)
        
        # 1. Try Load Cache (Parquet)
        if os.path.exists(cache_path):
            try:
                cached_df = pd.read_parquet(cache_path)
                # Check if covers range
                if not cached_df.empty:
                    cache_start = cached_df.index.min()
                    cache_end = cached_df.index.max()
                    
                    req_start = pd.to_datetime(start_date)
                    req_end = pd.to_datetime(end_date)
                    
                    if cache_start <= req_start and cache_end >= req_end:
                        return cached_df['sentiment'].loc[req_start:req_end]
            except Exception as e:
                self.logger.warning(f"Failed to read cache for {ticker}: {e}")

        # 2. Miss - Fetch & Compute
        self.logger.info(f"Sentiment Cache Miss for {ticker}. Fetching...")
        
        dates = pd.date_range(start=start_date, end=end_date)
        raw_scores = {}
        
        # Fetch headlines (Sequential for now as fetcher is per ticker)
        # If we had multiple tickers, we'd use concurrency here.
        # But for a single ticker over time, we might want to parallelize if we had date-based fetching.
        # Since NewsFetcher currently fetches "Top 5" regardless of date (Real-time limitation),
        # we just do one fetch.
        
        headlines = self.fetcher.fetch_headlines(ticker=ticker, market='US')
        
        # Group by date
        news_by_date = {}
        for item in headlines:
            try:
                pub_date = pd.to_datetime(item['published']).normalize()
                if pub_date not in news_by_date:
                    news_by_date[pub_date] = []
                news_by_date[pub_date].append(item)
            except:
                continue
                
        # Calculate scores (Parallelize LLM calls if multiple dates)
        if news_by_date:
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_date = {
                    executor.submit(self.analyzer.analyze_news, items, ticker): date 
                    for date, items in news_by_date.items()
                }
                
                for future in as_completed(future_to_date):
                    date = future_to_date[future]
                    try:
                        score = future.result()
                        raw_scores[date] = score
                    except Exception as e:
                        self.logger.error(f"Error analyzing news for {date}: {e}")

        # Apply Decay (Vectorized)
        if not raw_scores:
            series = pd.Series(0.0, index=dates, name='sentiment')
        else:
            series = self.decay_model.apply_decay(dates, raw_scores)
            series.name = 'sentiment'

        # 3. Save Cache (Parquet)
        if os.path.exists(cache_path):
            try:
                existing_df = pd.read_parquet(cache_path)
                combined_df = existing_df.combine_first(series.to_frame())
                combined_df.to_parquet(cache_path)
            except:
                series.to_frame().to_parquet(cache_path)
        else:
            series.to_frame().to_parquet(cache_path)
            
        return series
