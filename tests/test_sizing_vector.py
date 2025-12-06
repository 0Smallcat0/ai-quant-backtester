import pytest
import pandas as pd
import numpy as np
from src.strategies.sizing import SentimentSizer

class TestSentimentSizerVectorization:
    
    def test_scalar_input(self):
        """Test legacy scalar input support."""
        sizer = SentimentSizer(base_weight=1.0, min_sentiment_threshold=0.0)
        
        # Test Case 1: Neutral (0.0) -> 0.5 * 1.0 = 0.5
        assert sizer.get_target_weight(0.0) == 0.5
        
        # Test Case 2: Positive (1.0) -> 1.0
        assert sizer.get_target_weight(1.0) == 1.0
        
        # Test Case 3: Negative (-1.0) with threshold 0.0 -> Should return 0.0 (below threshold)
        # Wait, min_sentiment_threshold=0.0. -1.0 < 0.0 -> 0.0
        assert sizer.get_target_weight(-1.0) == 0.0
        
        # Test Case 4: Negative (-0.5) with threshold -1.0
        sizer_low_thresh = SentimentSizer(min_sentiment_threshold=-1.0)
        # weight = 0.5 + 0.5*(-0.5) = 0.25
        assert sizer_low_thresh.get_target_weight(-0.5) == 0.25

    def test_vector_input_series(self):
        """Test Pandas Series input (Vectorized)."""
        sizer = SentimentSizer(base_weight=1.0, min_sentiment_threshold=0.2)
        
        # Create series with mixed values
        # [Below Thresh, Thresh, Above Thresh, Max]
        sentiment = pd.Series([0.1, 0.2, 0.6, 1.0])
        
        weights = sizer.get_target_weight(sentiment)
        
        assert isinstance(weights, pd.Series)
        
        # Check Value 1: 0.1 < 0.2 -> 0.0
        assert weights[0] == 0.0
        
        # Check Value 2: 0.2 >= 0.2 -> 0.5 + 0.5*0.2 = 0.6
        assert np.isclose(weights[1], 0.6)
        
        # Check Value 3: 0.6 -> 0.5 + 0.5*0.6 = 0.8
        assert np.isclose(weights[2], 0.8)
        
        # Check Value 4: 1.0 -> 1.0
        assert np.isclose(weights[3], 1.0)

    def test_vector_input_numpy(self):
        """Test Numpy Array input."""
        sizer = SentimentSizer(base_weight=0.8, min_sentiment_threshold=0.0)
        
        arr = np.array([-0.5, 0.0, 0.5, 1.0])
        weights = sizer.get_target_weight(arr)
        
        # Value 1: -0.5 < 0.0 -> 0.0
        assert weights[0] == 0.0
        
        # Value 2: 0.0 >= 0.0 -> 0.8 * (0.5 + 0) = 0.4
        assert np.isclose(weights[1], 0.4)
        
        # Value 3: 0.5 -> 0.8 * (0.5 + 0.25) = 0.6
        assert np.isclose(weights[2], 0.6)
