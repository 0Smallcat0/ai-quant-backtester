from abc import ABC, abstractmethod
import numpy as np
import pandas as pd

class PositionSizer(ABC):
    """
    Abstract base class for position sizing strategies.
    """
    @abstractmethod
    def get_target_weight(self, signal_strength: float) -> float:
        """
        Calculates the target weight (0.0 to 1.0) based on signal strength.
        """
        pass

class SentimentSizer(PositionSizer):
    """
    Adjusts position size based on sentiment score.
    
    Logic:
    - If score < min_threshold: 0.0 (Risk Off)
    - Else: base_weight * (0.5 + 0.5 * score) * scale_factor
    """
    def __init__(self, base_weight: float = 1.0, min_sentiment_threshold: float = 0.2, scale_factor: float = 1.0, allow_leverage: bool = False):
        self.base_weight = base_weight
        self.min_threshold = min_sentiment_threshold
        self.scale_factor = scale_factor
        self.allow_leverage = allow_leverage

    def get_target_weight(self, sentiment_score: float | pd.Series | np.ndarray) -> float | pd.Series | np.ndarray:
        """
        Calculates the target weight based on sentiment score.
        Supports both scalar (float) and vector (Series/Array) inputs.
        """
        # Vectorized Implementation
        if isinstance(sentiment_score, (pd.Series, np.ndarray, list)):
            if isinstance(sentiment_score, list):
                sentiment_score = np.array(sentiment_score)
                
            # 1. Calculate Raw Weight (Broadcasting)
            # mapping = 0.5 + 0.5 * score
            mapping = 0.5 + 0.5 * sentiment_score
            target = self.base_weight * mapping * self.scale_factor
            
            # 2. Threshold & Clip Logic
            # target = np.where(score < min_thresh, 0.0, target)
            # Then clip to [0, 1] (or just >0 if leverage)
            
            # Use Numpy where for conditional logic
            if isinstance(target, pd.Series):
                 # Alignment safety
                 target = target.where(sentiment_score >= self.min_threshold, 0.0)
                 if not self.allow_leverage:
                     target = target.clip(lower=0.0, upper=1.0)
                 else:
                     target = target.clip(lower=0.0)
            else:
                 target = np.where(sentiment_score < self.min_threshold, 0.0, target)
                 if not self.allow_leverage:
                     target = np.clip(target, 0.0, 1.0)
                 else:
                     target = np.clip(target, 0.0, None)
            
            return target

        # Scalar Implementation (Legacy/Single)
        # 1. Threshold Check
        if sentiment_score < self.min_threshold:
            return 0.0
            
        # 2. Calculate Raw Weight
        mapping = 0.5 + 0.5 * sentiment_score
        target = self.base_weight * mapping * self.scale_factor
        
        # 3. Clip
        if not self.allow_leverage:
            target = min(1.0, max(0.0, target))
        else:
            target = max(0.0, target)
            
        return target
