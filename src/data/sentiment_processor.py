import json
import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from src.ai.llm_client import LLMClient
from src.ai.prompts import SENTIMENT_ANALYSIS_PROMPT
from src.config.settings import settings
import re

class SentimentAnalyzer:
    """
    Analyzes news sentiment using LLM.
    """
    """
    Analyzes news sentiment using LLM.
    """
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client if llm_client else LLMClient()
        self.system_prompt = SENTIMENT_ANALYSIS_PROMPT
        self.logger = logging.getLogger(__name__)

    def analyze_news(self, news_list: List[Dict], ticker: str) -> float:
        """
        Generates a sentiment score (-1.0 to 1.0) for the given news list.
        """
        if not news_list:
            return 0.0

        # 1. Compact Format & Smart Truncation
        # Limit each news item to 500 chars to ensure diversity in context
        MAX_ITEM_LEN = 500
        full_text = ""
        for idx, item in enumerate(news_list, 1):
            title = item.get('title', 'No Title')
            summary = item.get('summary', 'No Summary')
            # Combine and truncate
            entry = f"{idx}. {title} ({summary})"
            if len(entry) > MAX_ITEM_LEN:
                entry = entry[:MAX_ITEM_LEN] + "..."
            full_text += f"{entry}\n"

        # 2. Global Truncation (Safety Net)
        if len(full_text) > settings.LLM_MAX_INPUT_CHARS:
            full_text = full_text[:settings.LLM_MAX_INPUT_CHARS] + "...(truncated)"

        # 3. Call LLM
        prompt = f"Ticker: {ticker}\n\nNews:\n{full_text}"
        
        # Format system prompt with ticker
        formatted_system_prompt = self.system_prompt.replace("{Ticker}", ticker)

        messages = [
            {"role": "system", "content": formatted_system_prompt},
            {"role": "user", "content": prompt}
        ]

        try:
            # Use temperature=0.0 for deterministic, analytical output
            response_str = self.llm_client.get_completion(messages=messages, temperature=0.0)
            
            # 4. Parse JSON with Regex (Robustness)
            cleaned_response = self.llm_client.clean_code(response_str)
            
            try:
                # Attempt to find JSON object pattern
                match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    data = json.loads(json_str)
                else:
                    # Fallback to direct load if regex fails (unlikely but safe)
                    data = json.loads(cleaned_response)
            except json.JSONDecodeError:
                self.logger.warning(f"JSON Decode Error for {ticker}. Response: {cleaned_response[:100]}...")
                return 0.0
                
            score = float(data.get('score', 0.0))
            
            # Clamp score just in case
            return max(-1.0, min(1.0, score))

        except Exception as e:
            self.logger.error(f"Error analyzing sentiment for {ticker}: {e}")
            return 0.0


class DecayModel:
    """
    Applies exponential decay to sentiment scores over time.
    """
    def __init__(self, half_life_days: Optional[float] = None):
        self.half_life = half_life_days if half_life_days is not None else settings.SENTIMENT_DECAY_HALFLIFE
        self.lambda_param = np.log(2) / self.half_life
        self.noise_threshold = settings.SENTIMENT_NOISE_THRESHOLD

    def apply_decay(self, dates: pd.DatetimeIndex, raw_scores: Dict[pd.Timestamp, float]) -> pd.Series:
        """
        Fills missing dates with decayed scores using vectorized operations.
        
        Args:
            dates: The full range of dates to cover.
            raw_scores: A dictionary mapping Date -> Raw Score (from LLM).
            
        Returns:
            pd.Series with index=dates and values=decayed_scores.
        """
        # Create a Series with all dates
        series = pd.Series(index=dates, dtype=float).sort_index()
        
        # Fill with raw scores where available
        for date, score in raw_scores.items():
            if date in series.index:
                series[date] = score
        
        # Forward fill with decay
        
        df = pd.DataFrame(index=dates)
        df['raw_score'] = pd.Series(raw_scores)
        
        # Forward fill the raw score (this gives us the base for decay)
        df['last_score'] = df['raw_score'].ffill()
        
        # Create a column for "date of last score"
        df['has_news'] = df['raw_score'].notna()
        # Use pd.to_datetime to ensure we have datetime objects, not mixed types
        df['last_news_date'] = pd.Series(np.where(df['has_news'], df.index, pd.NaT), index=df.index)
        df['last_news_date'] = pd.to_datetime(df['last_news_date']).ffill()
        
        # Calculate days elapsed
        # Convert index to series for subtraction
        current_dates = pd.Series(df.index, index=df.index)
        df['days_elapsed'] = (current_dates - df['last_news_date']).dt.days
        
        # Calculate decay
        # S_t = LastScore * exp(-lambda * days)
        # Handle NaNs (start of period before any news) -> 0.0
        
        df['decayed_score'] = df['last_score'] * np.exp(-self.lambda_param * df['days_elapsed'])
        df['decayed_score'] = df['decayed_score'].fillna(0.0)
        
        # Noise filter
        df.loc[df['decayed_score'].abs() < self.noise_threshold, 'decayed_score'] = 0.0
        
        return df['decayed_score']

