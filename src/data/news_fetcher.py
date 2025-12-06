import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Optional
from src.config.settings import settings
import re
from datetime import datetime, timedelta
import pytz
from dateutil import parser
import difflib
from cachetools import TTLCache, cached
import requests

class NewsFetcher:
    """
    Fetches news from Google News RSS and cleans the output.
    """
    def __init__(self):
        self.base_urls = settings.NEWS_BASE_URLS
        self.sources = settings.NEWS_SOURCES
        self.logger = logging.getLogger(__name__)
        # [OPTIMIZATION] Resilience: User-Agent and Timeout
        self.request_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.timeout = settings.DEFAULT_TIMEOUT
        
        # [OPTIMIZATION] Performance: TTL Cache (100 items, 5 mins)
        # Note: We cannot easily use @cached decorator on method with self if cache is instance-bound.
        # But we can use a dict. Or use methodtools.
        # For simplicity, let's use a simple dict with timestamp check or cachetools.TTLCache
        self._cache = TTLCache(maxsize=100, ttl=300)

    def _build_query(self, ticker: str, name: Optional[str] = None, market: str = 'US') -> str:
        """
        Constructs the Google News RSS URL with advanced query operators.
        """
        if market not in self.base_urls:
            raise ValueError(f"Unsupported market: {market}")

        # 1. Build the search terms part: "{Name}" OR "{Ticker}"
        search_terms = []
        if name:
            search_terms.append(f'"{name}"')
        if ticker:
            search_terms.append(f'"{ticker}"')
        
        term_query = " OR ".join(search_terms)
        
        # 2. Build the site filter part: site:A OR site:B ...
        sites = self.sources.get(market, [])
        site_query = " OR ".join(sites)
        
        full_query = f"{term_query} {site_query}"
        
        # 4. URL Encode
        encoded_query = urllib.parse.quote(full_query)
        
        # 5. Inject into Base URL
        base_url = self.base_urls[market]
        final_url = base_url.replace("{ENCODED_QUERY}", encoded_query)
        
        return final_url

    def _clean_html(self, raw_html: str) -> str:
        """
        Removes HTML tags and cleans up text.
        """
        soup = BeautifulSoup(raw_html, "html.parser")
        text = soup.get_text(separator=" ")
        return text.strip()

    def _filter_noise(self, entries: List[Dict], market: str) -> List[Dict]:
        """
        Filters out noise (listicles, reports) and duplicates.
        """
        filtered = []
        seen_titles = set()
        
        # Blocklist for TW market
        NOISE_KEYWORDS = settings.NEWS_NOISE_KEYWORDS
        
        for entry in entries:
            title = entry.get('title', '').strip()
            if not title:
                continue
                
            # 1. Deduplication (Fuzzy Match)
            is_duplicate = False
            for seen_title in seen_titles:
                # Calculate similarity
                similarity = difflib.SequenceMatcher(None, title, seen_title).ratio()
                if similarity > 0.7: # Threshold
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue
            
            # 2. Noise Filtering (TW only mostly)
            is_noise = False
            if market == 'TW':
                for keyword in NOISE_KEYWORDS:
                    if keyword in title:
                        is_noise = True
                        break
            
            if not is_noise:
                filtered.append(entry)
                seen_titles.add(title)
                
        return filtered

    def _normalize_date(self, published_str: str, market: str) -> str:
        """
        Parses published date, converts to market local time, and applies rollover logic.
        Returns 'YYYY-MM-DD' string.
        """
        try:
            # 1. Parse UTC/GMT time
            dt_utc = parser.parse(published_str)
            
            # Ensure it is timezone-aware
            if dt_utc.tzinfo is None:
                dt_utc = dt_utc.replace(tzinfo=pytz.UTC)
            else:
                dt_utc = dt_utc.astimezone(pytz.UTC)

            # 2. Define Market Timezone & Cutoff
            tz_name = settings.MARKET_TIMEZONES.get(market, 'UTC')
            cutoff_hour = settings.MARKET_ROLLOVER_HOURS.get(market, 24)
            
            tz = pytz.timezone(tz_name)

            # 3. Convert to Local Time
            dt_local = dt_utc.astimezone(tz)
            
            # 4. Rollover Logic
            # If hour >= cutoff, move to next day
            if dt_local.hour >= cutoff_hour:
                effective_date = dt_local.date() + timedelta(days=1)
            else:
                effective_date = dt_local.date()
                
            return effective_date.strftime('%Y-%m-%d')
            
        except Exception as e:
            logging.getLogger(__name__).warning(f"Date parsing failed for {published_str}: {e}")
            # Fallback to today's date if parsing fails
            return datetime.now().strftime('%Y-%m-%d')

    def _calculate_impact_score(self, title: str, link: str, market: str) -> float:
        """
        Calculates impact score based on keywords and source.
        """
        scores = settings.NEWS_IMPACT_SCORES
        score = scores.get('BASE_SCORE', 1.0)
        title_lower = title.lower()
        
        # Keyword Lists
        impact_kws = settings.NEWS_IMPACT_KEYWORDS.get(market, {})
        tier_1 = impact_kws.get('TIER_1', [])
        tier_2 = impact_kws.get('TIER_2', [])
        
        # Source Bonus List
        premium_sources = settings.NEWS_PREMIUM_SOURCES
        
        # 1. Keyword Bonus
        # For TW, keywords are usually Chinese, case sensitivity matters less for Chinese characters but good to be safe.
        # For US, we use lowercase.
        
        # Check Tier 1
        for kw in tier_1:
            if kw in (title if market == 'TW' else title_lower):
                score += scores.get('TIER_1', 10.0)
                break
        
        # Check Tier 2
        for kw in tier_2:
            if kw in (title if market == 'TW' else title_lower):
                score += scores.get('TIER_2', 5.0)
                break
                    
        # 2. Source Bonus
        for src in premium_sources:
            if src in link:
                score += scores.get('SOURCE_BONUS', 3.0)
                break
                
        return score

    def fetch_headlines(self, ticker: str, name: Optional[str] = None, market: str = 'US') -> List[Dict[str, str]]:
        """
        Fetches top 5 news headlines after filtering and ranking.
        Returns empty list on failure.
        """
        # Warning about Look-ahead Bias
        logging.getLogger(__name__).warning(f"Fetching REAL-TIME news for {ticker}. CAUTION: This may introduce look-ahead bias if used for historical backtesting.")
        
        # Check Cache
        cache_key = f"{ticker}_{market}"
        if cache_key in self._cache:
            self.logger.info(f"Cache Hit for {ticker}")
            return self._cache[cache_key]
            
        try:
            url = self._build_query(ticker, name, market)
            
            # [OPTIMIZATION] Resilience: Use requests with timeout and headers, then parse string
            # feedparser's remote fetching is flaky.
            import requests
            response = requests.get(url, headers=self.request_headers, timeout=self.timeout)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            
            headlines = []
            # Fetch 100 first, then filter (Increased to 100 to ensure top-5 survival)
            all_entries = feed.entries[:100]
            count_fetched = len(all_entries)
            
            # Apply Filtering
            clean_entries = self._filter_noise(all_entries, market)
            count_after_noise = len(clean_entries)
            
            # --- Impact Ranking ---
            scored_entries = []
            for entry in clean_entries:
                title = entry.get('title', '')
                link = entry.get('link', '')
                score = self._calculate_impact_score(title, link, market)
                scored_entries.append((score, entry))
            
            # Sort by Score (Desc)
            scored_entries.sort(key=lambda x: x[0], reverse=True)
            
            # Extract sorted entries
            sorted_entries = [x[1] for x in scored_entries]
            # ----------------------
            
            # Limit to Top N (from settings)
            limit = settings.NEWS_TOP_N_LIMIT
            final_entries = sorted_entries[:limit]
            count_final = len(final_entries)
            
            # [OPTIMIZATION] Observability: Funnel Metrics
            self.logger.info(f"News Funnel for {ticker}: Fetched={count_fetched} -> NoiseFiltered={count_after_noise} -> Final={count_final}")
            
            for entry in final_entries:
                summary = self._clean_html(entry.get('summary', ''))
                published = entry.get('published', '')
                
                # Normalize Date
                date_str = self._normalize_date(published, market)
                
                headlines.append({
                    "title": entry.get('title', ''),
                    "link": entry.get('link', ''),
                    "published": published,
                    "date": date_str,
                    "summary": summary
                })
                
            # Update Cache
            self._cache[cache_key] = headlines
            return headlines
            
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to fetch news for {ticker}: {e}")
            return []
