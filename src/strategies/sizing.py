from abc import ABC, abstractmethod
import numpy as np

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

    def get_target_weight(self, sentiment_score: float) -> float:
        # 1. Threshold Check
        if sentiment_score < self.min_threshold:
            return 0.0
            
        # 2. Calculate Raw Weight
        # Mapping: -1.0 -> 0.0, 1.0 -> 1.0 (if base=1)
        # But wait, the formula (0.5 + 0.5 * score) implies:
        # Score 1.0 -> 1.0
        # Score 0.0 -> 0.5
        # Score -1.0 -> 0.0
        # This seems correct for a "long only" mapping where negative sentiment reduces size but doesn't go short (unless we want short).
        # The user said: "target_weight = base_weight * (0.5 + 0.5 * score)"
        
        mapping = 0.5 + 0.5 * sentiment_score
        target = self.base_weight * mapping * self.scale_factor
        
        # 3. Clip
        if not self.allow_leverage:
            target = min(1.0, max(0.0, target))
        else:
            target = max(0.0, target)
            
        return target
