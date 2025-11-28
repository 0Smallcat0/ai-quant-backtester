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
                
            sentiment = float(data.get('sentiment', 0.0))
            relevance = float(data.get('relevance', 0.0))
            
            # Clamp values
            sentiment = max(-1.0, min(1.0, sentiment))
            relevance = max(0.0, min(1.0, relevance))
            
            final_score = sentiment * relevance
            return final_score

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
        Applies linear superposition decay.
        S_t = Sum(Score_i * exp(-lambda * (t - t_i)))
        
        Args:
            dates: The full range of dates to cover.
            raw_scores: A dictionary mapping Date -> Raw Score (from LLM).
            
        Returns:
            pd.Series with index=dates and values=decayed_scores.
        """
        # Create a Series with all dates, initialized to 0
        # We use a sparse approach: create a series of raw scores aligned to dates
        raw_series = pd.Series(0.0, index=dates)
        
        # Fill in the raw scores
        for date, score in raw_scores.items():
            if date in raw_series.index:
                # If multiple news on same day, we could sum them or take max. 
                # Here we assume one score per day or sum if pre-aggregated.
                # If raw_scores is just a dict, it overwrites. 
                # Ideally raw_scores should be handled carefully if multiple events.
                # But for now, let's assume the input dict has unique dates.
                raw_series[date] = score

        # Optimization:
        # Instead of double loop, we can use a recursive formulation or convolution.
        # Recursive: S_t = S_{t-1} * decay + NewScore_t
        # But this is only true if time steps are uniform (1 day).
        # Since 'dates' is a DatetimeIndex with freq='D' (usually), we can assume uniform steps.
        
        # Let's verify frequency. If not uniform, we must use the exact time difference.
        # For robustness, let's use the exact formula with a lookback window.
        # However, full O(N^2) is slow.
        # The recursive formula S_t = S_{t-1} * exp(-lambda * dt) + Raw_t is O(N).
        
        decayed_values = []
        last_val = 0.0
        last_date = dates[0]
        
        # We iterate through the dates. 
        # Note: raw_series contains 0.0 where no news.
        
        # Pre-convert to numpy for speed
        date_values = dates.values
        raw_values = raw_series.values
        
        # We need time deltas in days.
        # Let's assume daily frequency for the loop to keep it simple and fast.
        # If dates are missing (gaps), we calculate exact delta.
        
        for i in range(len(dates)):
            current_date = date_values[i]
            raw_val = raw_values[i]
            
            if i == 0:
                # First day
                s_t = raw_val
            else:
                # Calculate days elapsed since last step
                # (current_date - last_date) in days
                # numpy timedelta64 to float days
                delta_days = (current_date - last_date) / np.timedelta64(1, 'D')
                
                decay_factor = np.exp(-self.lambda_param * delta_days)
                s_t = last_val * decay_factor + raw_val
            
            decayed_values.append(s_t)
            last_val = s_t
            last_date = current_date
            
        result_series = pd.Series(decayed_values, index=dates)
        
        # Noise filter
        result_series[result_series.abs() < self.noise_threshold] = 0.0
        
        return result_series

