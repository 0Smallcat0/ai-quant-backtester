import os
import pandas as pd
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from src.data.news_fetcher import NewsFetcher
from src.data.sentiment_processor import SentimentAnalyzer, DecayModel
from src.ai.llm_client import LLMClient
from src.ai.translator import TextTranslator
import threading

try:
    from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
except ImportError:
    def add_script_run_ctx(thread, ctx=None): pass
    def get_script_run_ctx(): return None

class NewsEngine:
    """
    Orchestrates news fetching, sentiment analysis, and caching.
    """
    def __init__(self, 
                 cache_dir: str = "data/sentiment_cache",
                 fetcher: Optional[NewsFetcher] = None,
                 analyzer: Optional[SentimentAnalyzer] = None,
                 decay_model: Optional[DecayModel] = None,

                 llm_client: Optional[LLMClient] = None,
                 translator: Optional[TextTranslator] = None):
        
        self.cache_dir = cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
        self.llm_client = llm_client if llm_client else LLMClient()
        self.fetcher = fetcher if fetcher else NewsFetcher()
        self.analyzer = analyzer if analyzer else SentimentAnalyzer(llm_client=self.llm_client)
        self.decay_model = decay_model if decay_model else DecayModel()
        self.translator = translator if translator else TextTranslator(llm_client=self.llm_client)
        self.logger = logging.getLogger(__name__)

    def _get_cache_path(self, ticker: str) -> str:
        # Use Parquet for better performance
        return os.path.join(self.cache_dir, f"{ticker}.parquet")

    def _process_translation(self, items: list) -> list:
        """
        Translates non-English titles in the list of news items.
        Returns the modified list.
        """
        import re
        
        # 1. Identify items needing translation
        indices_to_translate = []
        texts_to_translate = []
        
        for i, item in enumerate(items):
            title = item.get('title', '')
            # Regex to detect CJK characters (common range)
            if re.search(r'[\u4e00-\u9fa5]', title):
                indices_to_translate.append(i)
                texts_to_translate.append(title)
        
        if not texts_to_translate:
            return items
            
        self.logger.info(f"Translating {len(texts_to_translate)} items.")
        
        # 2. Batch Translate
        # [Log Before]
        for txt in texts_to_translate:
            self.logger.debug(f"DEBUG - Original Text: {txt}")

        translated_texts = self.translator.translate_batch(texts_to_translate)
        
        # [Log After & Quality Check]
        for i, original in enumerate(texts_to_translate):
            if i < len(translated_texts):
                trans = translated_texts[i]
                self.logger.debug(f"DEBUG - Translated Text: {trans}")
                
                # Check for failed translation (Empty or Identical while being Chinese)
                if not trans or (trans == original and re.search(r'[\u4e00-\u9fa5]', original)):
                    self.logger.warning(f"Translation might have failed (returned identical or empty) for: {original}")
        
        # 3. Apply translations
        for idx_in_batch, original_idx in enumerate(indices_to_translate):
            if idx_in_batch < len(translated_texts):
                items[original_idx]['title'] = translated_texts[idx_in_batch]
                # Optional: Store original title if needed for debugging
                # items[original_idx]['original_title'] = texts_to_translate[idx_in_batch]
                
        return items

    @staticmethod
    def _analyze_wrapper(ctx, func, *args):
        """Helper to run analysis with Streamlit context in thread."""
        if ctx:
            add_script_run_ctx(threading.current_thread(), ctx)
        return func(*args)

    def _fetch_and_analyze(self, ticker: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.Series:
        """
        Fetch, translate, analyze news and apply decay.
        Returns a sentiment score Series.
        If start_date/end_date provided, returns Series covering that range (filling 0 if no news).
        If not provided, returns Series covering found news dates.
        """
        # Fetch
        headlines = self.fetcher.fetch_headlines(ticker=ticker, market='US')
        
        # Group by date
        news_by_date = {}
        if headlines:
            for item in headlines:
                try:
                    pub_date = pd.to_datetime(item['published']).normalize()
                    if pub_date not in news_by_date:
                        news_by_date[pub_date] = []
                    news_by_date[pub_date].append(item)
                except:
                    continue
        
        if not news_by_date:
            if start_date and end_date:
                 dates = pd.date_range(start=start_date, end=end_date)
                 return pd.Series(0.0, index=dates, name='sentiment')
            return pd.Series(dtype=float)

        # Analyze (Threaded)
        raw_scores = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            ctx = get_script_run_ctx()
            future_to_date = {}
            for date, items in news_by_date.items():
                # Translation
                translated_items = self._process_translation(items)
                
                # Analysis
                if ctx:
                    future = executor.submit(self._analyze_wrapper, ctx, self.analyzer.analyze_news, translated_items, ticker)
                else:
                    future = executor.submit(self.analyzer.analyze_news, translated_items, ticker)
                future_to_date[future] = date

            for future in as_completed(future_to_date):
                date = future_to_date[future]
                try:
                    score = future.result()
                    raw_scores[date] = score
                except Exception as e:
                    self.logger.error(f"Error analyzing news for {date}: {e}")

        # Apply Decay
        if start_date and end_date:
            target_dates = pd.date_range(start=start_date, end=end_date)
        else:
            sorted_dates = sorted(raw_scores.keys())
            if not sorted_dates:
                 return pd.Series(dtype=float)
            target_dates = pd.DatetimeIndex(sorted_dates)

        series = self.decay_model.apply_decay(target_dates, raw_scores)
        series.name = 'sentiment'
        return series

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
        
        series = self._fetch_and_analyze(ticker, start_date, end_date)

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

    def update_cache_smart(self, ticker: str, days_threshold: int = 3) -> None:
        """
        Smart update: Only fetch new news if cache is old or missing.
        """
        cache_path = self._get_cache_path(ticker)
        
        # 1. Check Recency
        if os.path.exists(cache_path):
            try:
                mtime = os.path.getmtime(cache_path)
                last_updated = datetime.fromtimestamp(mtime)
                
                # Check delta
                if (datetime.now() - last_updated).days < days_threshold:
                    self.logger.info(f"Skipping sentiment update for {ticker} (Last updated: {last_updated.date()})")
                    return
            except Exception as e:
                self.logger.warning(f"Failed to check cache mtime for {ticker}, forcing update: {e}")

        # 2. Update (Fault Tolerant)
        self.logger.info(f"Triggering smart update for {ticker}...")
        try:
            series = self._fetch_and_analyze(ticker)
            
            if series.empty:
                 self.logger.info(f"No news found for {ticker}.")
                 if os.path.exists(cache_path):
                     os.utime(cache_path, None)
                 return

            # Save/Merge
            if os.path.exists(cache_path):
                try:
                    existing_df = pd.read_parquet(cache_path)
                    combined_df = existing_df.combine_first(series.to_frame())
                    combined_df.to_parquet(cache_path)
                except:
                    series.to_frame().to_parquet(cache_path)
            else:
                series.to_frame().to_parquet(cache_path)
                
            self.logger.info(f"Smart update completed for {ticker}")
            
        except Exception as e:
            self.logger.error(f"Smart update failed for {ticker}: {e}")
