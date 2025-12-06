
import pandas as pd
import numpy as np
from typing import List, Dict, Union

class SentimentFactorEngine:
    """
    Computes final sentiment factors by applying Impact Weighting.
    Formula: Signal = Sentiment * Relevance
    """
    def __init__(self):
        pass

    def compute_signal(self, news_items: List[Dict], sentiment_score: float) -> float:
        """
        Computes the weighted signal for a ticker based on a list of news items
        and the aggregate sentiment score derived from them.
        
        Args:
            news_items: List of news dicts (must contain 'relevance_score' or similar if available, 
                        currently relying on heuristic or LLM output). 
                        However, the current architecture calculates One Sentiment Score for the whole list.
            sentiment_score: The aggregate sentiment score (-1.0 to 1.0) from SentimentAnalyzer.
            
        Returns:
            Review the architecture: 
            The user report says: "Final_Score = Polarity * Relevance".
            
            If we have a single aggregated sentiment_score, we need an aggregated relevance score.
            In 'analyze_news', relevance was implicitly handled by the LLM (Aspects).
            
            Let's assume this Engine is used to post-process the raw sentiment score 
            with additional metadata-based relevance (e.g., Tier 1 sources).
            
            For simplicity and adherence to the prompt: 
            We calculate an average relevance score from the news items metadata if available,
            or default to 1.0.
        """
        if not news_items:
            return 0.0
            
        # Extract relevance if available, else default to 1.0
        relevance_scores = []
        for item in news_items:
            # Check for 'relevance' key (e.g. from LLM or metadata)
            # If not present, check impact tier
            rel = item.get('relevance_score', 1.0) 
            relevance_scores.append(rel)
            
        avg_relevance = np.mean(relevance_scores) if relevance_scores else 0.0
        
        final_signal = sentiment_score * avg_relevance
        
        # Clamp
        return max(-1.0, min(1.0, final_signal))

    def compute_factor_series(self, sentiment_series: pd.Series, relevance_series: pd.Series) -> pd.Series:
        """
        Vectorized computation for backtesting.
        """
        return sentiment_series * relevance_series
