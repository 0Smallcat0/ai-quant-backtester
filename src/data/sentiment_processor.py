import json
import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from src.config.settings import settings
from src.analytics.sentiment.finbert_analyzer import FinBERTAnalyzer
from src.analytics.sentiment.absa_analyzer import ABSAAnalyzer

class SentimentAnalyzer:
    """
    Modernized hybrid sentiment analyzer:
    1. Filter: FinBERT (Tone Analysis)
    2. Analyze: LLM ABSA (Aspect-Based)
    3. Synthesize: Weighted Scoring
    """
    def __init__(self, llm_client: Optional[object] = None):
        self.logger = logging.getLogger(__name__)
        self.mode = settings.SENTIMENT_MODEL_TYPE
        self.llm_client = llm_client
        
        # Lazy loading to save resources if not used
        self.finbert = None
        self.absa = None

    def _load_models(self):
        if self.finbert is None:
            try:
                self.finbert = FinBERTAnalyzer(model_name=settings.FINBERT_PATH)
            except Exception as e:
                self.logger.error(f"Failed to load FinBERT: {e}")
                
        if self.absa is None:
            try:
                self.absa = ABSAAnalyzer(llm_client=self.llm_client, model_id=settings.ABSA_MODEL_PATH)
            except Exception as e:
                self.logger.error(f"Failed to load ABSA: {e}")

    def analyze_news(self, news_list: List[Dict], ticker: str) -> float:
        """
        Generates a sentiment score (-1.0 to 1.0) for the given news list using Hybrid Pipeline.
        """
        if not news_list:
            return 0.0

        if self.mode != "local_hybrid":
            self.logger.warning("Legacy mode not supported in this version. Please set SENTIMENT_MODEL_TYPE='local_hybrid'")
            return 0.0

        self._load_models()
        if not self.finbert or not self.absa:
             self.logger.error("Models not loaded. Returning 0.")
             return 0.0

        # Step 1: Pre-process and Batch for FinBERT
        processed_texts = []
        original_map = [] # Map index to original item
        
        for item in news_list:
            title = item.get('title', '')
            summary = item.get('summary', '')
            text = f"{title}. {summary}"
            processed_texts.append(text)
            original_map.append(item)

        # Step 2: FinBERT Filter
        try:
            finbert_results = self.finbert.predict(processed_texts)
        except Exception as e:
            self.logger.error(f"FinBERT prediction failed: {e}")
            return 0.0

        high_confidence_items = []
        
        # Filter logic
        for i, res in enumerate(finbert_results):
            neutral_score = res.get('Neutral', 0.0)
            if neutral_score > settings.SENTIMENT_FILTER_THRESHOLD: # > 0.85
                continue # Skip noise
            
            # Keep interesting items
            # We pass the text and the FinBERT score to the next stage
            high_confidence_items.append({
                'text': processed_texts[i],
                'finbert_score': res, # {'Positive', 'Negative', 'Neutral'}
                'original': original_map[i]
            })

        if not high_confidence_items:
            self.logger.info(f"No significant news found for {ticker} after filtering.")
            return 0.0

        # Step 3: LLM ABSA Analysis (OPTIMIZED COST-SAVING)
        # We only analyze items where FinBERT is "Sure but needs nuance"
        # If FinBERT is weak (Polarity < 0.5), we trust FinBERT alone and save LLM token cost.
        
        absa_results_map = {} # Map index in high_confidence_items -> absa_result
        texts_to_analyze = []
        indices_to_analyze = []
        
        for idx, item in enumerate(high_confidence_items):
            fin_res = item['finbert_score']
            polarity = fin_res['Positive'] - fin_res['Negative']
            item['polarity'] = polarity # Store for synthesis
            
            # THE ANALYST GATEKEEPER
            if abs(polarity) > 0.5:
                texts_to_analyze.append(item['text'])
                indices_to_analyze.append(idx)
            # Else: skip LLM, use default neutral structure
        
        if texts_to_analyze:
            try:
                batch_results = self.absa.analyze_batch(texts_to_analyze)
                for i, res in enumerate(batch_results):
                    absa_results_map[indices_to_analyze[i]] = res
            except Exception as e:
                self.logger.error(f"ABSA prediction failed: {e}")
                # Fallbck: map stays empty

        # Step 4: Signal Synthesis
        total_score = 0.0
        count = 0
        
        for i, item in enumerate(high_confidence_items):
            f_score = item['polarity']
            
            # Check if we have ABSA result
            if i in absa_results_map:
                absa_res = absa_results_map[i]
                
                a_sentiment = absa_res.get('Overall_Sentiment', 'Neutral')
                a_score = 0.0
                if a_sentiment == 'Positive':
                    a_score = 1.0
                elif a_sentiment == 'Negative':
                    a_score = -1.0
                
                # Check for aspects (Boost score if aspect is relevant)
                aspect_boost = 1.0
                if absa_res.get('Positive_Aspect') or absa_res.get('Negative_Aspect'):
                    aspect_boost = 1.2
                
                # Weighted Combination: 60% FinBERT, 40% ABSA
                combined_score = (0.6 * f_score + 0.4 * a_score) * aspect_boost
            
            else:
                # Fallback: Trust FinBERT alone (Weak signal)
                # Since polarity is low (<0.5), we allow it to pass but it will be weak.
                # Logic: We treat ABSA score as 0 (Neutral/Unknown) in the weighted mix
                # Combined = 0.6 * FinBERT + 0.4 * 0 = 0.6 * FinBERT
                combined_score = 0.6 * f_score 

            total_score += combined_score
            count += 1
            
        if count == 0:
            return 0.0
            
        final_avg_score = total_score / count
        
        # Clamp
        final_avg_score = max(-1.0, min(1.0, final_avg_score))
        
        return final_avg_score

class DecayModel:
    """
    Applies exponential decay to sentiment scores over time.
    """
    def __init__(self, half_life_days: Optional[float] = None):
        self.half_life = half_life_days if half_life_days is not None else settings.SENTIMENT_DECAY_HALFLIFE
        self.lambda_param = np.log(2) / self.half_life
        # [FIX] Lower threshold to avoid "Dead Fish" on subtle news
        self.noise_threshold = 0.01 # Was settings.SENTIMENT_NOISE_THRESHOLD or 0.1

    def apply_decay(self, dates: pd.DatetimeIndex, raw_scores: Dict[pd.Timestamp, float]) -> pd.Series:
        """
        Applies exponential decay to sentiment scores over time using Vectorized operations.
        """
        # 1. Align Raw Scores to Full Date Range
        # Create a Series with NaNs where there is no score
        raw_series = pd.Series(np.nan, index=dates)
        
        # Fill only existing dates (Much faster than iterating)
        # We need to construct a Series from the dict and then reindex
        # But for safety/robustness with duplicates in dict (if any), let's do:
        incoming_series = pd.Series(raw_scores)
        # Align to our target index
        # We assume dates is sorted and unique mostly, but let's be safe
        aligned_scores = incoming_series.reindex(dates) 
        
        # 2. Fill NaNs with previous values (Forward Fill) for standard decay continuity?
        # WAIT: The original logic was:
        # s_t = (last_val * decay) + (new_val * (1-decay))
        # If new_val is 0 (missing), we want s_t = last_val * decay (pure decay)
        # ewm(adjust=False) implements: y_t = (1-a)*y_{t-1} + a*x_t
        # This assumes x_t exists.
        
        # If x_t is missing (0 implicit in original logic?), the original logic said:
        # "raw_series = pd.Series(0.0...)" -> Default was 0.0.
        # "raw_series[date] = score"
        
        # Original Logic Analysis:
        # if i==0: s_t = raw
        # else: s_t = last * decay + raw * (1-decay)
        # raw is 0.0 if not present.
        
        # So it equates to: Update with 0.0 ("Neutral/Msg") if no news.
        # This means sentiment decays towards 0.0.
        
        # Implementation with EWM:
        # Fill missing with 0.0
        aligned_scores = aligned_scores.fillna(0.0)
        
        # Clamp inputs
        aligned_scores = aligned_scores.clip(-1.0, 1.0)
        
        # EWM
        # Note: pandas ewm assumes constant time steps if 'times' not provided.
        # dates passed in IS the time index.
        # We use 'halflife' argument which handles the decay factor calculation automatically.
        # ewm(halflife='5 days', times=dates) is supported in pandas >= 1.2
        
        try:
             # Try modern pandas times-based ewm
             result_series = aligned_scores.ewm(halflife=f"{self.half_life} days", times=dates, adjust=False).mean()
        except Exception:
             # Fallback for older pandas or if dates index is not DatetimeIndex compatible
             # Assume daily steps if we can't use times
             result_series = aligned_scores.ewm(halflife=self.half_life, adjust=False).mean()
             
        # Clamp result
        result_series = result_series.clip(-1.0, 1.0) # clip is vectorized max/min
        
        # Noise Filter
        result_series[result_series.abs() < self.noise_threshold] = 0.0
        
        return result_series
