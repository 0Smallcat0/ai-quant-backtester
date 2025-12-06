import pytest
import pandas as pd
import numpy as np
import sys
import os

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.data.sentiment_processor import DecayModel

class TestSentimentDecay:
    def test_additive_impulse_accumulation(self):
        """
        Test that continuous positive news ACCUMULATES sentiment (Additive Impulse),
        instead of just averaging it.
        """
        model = DecayModel(half_life_days=3)
        dates = pd.date_range(start="2024-01-01", periods=10, freq='D')
        
        # Scenario: 10 days of medium sentiment (0.5)
        # New Logic (Additive): 0.5 -> Accumulated -> Saturation at 1.0
        # This proves we fixed the "Damping" issue where weak signals stayed weak.
        raw_scores = {d: 0.5 for d in dates}
        
        result_series = model.apply_decay(dates, raw_scores)
        
        print("\nDecay Series Results:")
        print(result_series)
        
        # Check Max Value
        max_val = result_series.max()
        # It SHOULD grow significantly beyond 0.5 now, verifying accumulation
        assert max_val > 0.8, f"Sentiment Score should have accumulated towards 1.0, but stayed at {max_val}"
        
        # Check Saturation
        assert max_val <= 1.0, "Sentiment Score should be clamped at 1.0"

    def test_decay_toward_zero(self):
        """Test that sentiment decays toward zero when no news."""
        model = DecayModel(half_life_days=1) # Fast decay
        dates = pd.date_range(start="2024-01-01", periods=4, freq='D')
        
        # Day 1: 1.0, then Silence
        raw_scores = {dates[0]: 1.0}
        
        result = model.apply_decay(dates, raw_scores)
        
        # Day 1: 1.0
        assert abs(result.iloc[0] - 1.0) < 1e-6
        # Day 2: Should adhere to decay formula (e^-lambda) approx 0.5
        # If Accumulative: 1.0 * 0.5 + 0 = 0.5 (Same for simple decay)
        # If Weighted Avg: 1.0 * 0.5 + 0 * 0.5 = 0.5 (Same for silence)
        
        # The key diff is when news is PRESENT, not absent.
        # But let's check it decays
        assert result.iloc[1] < result.iloc[0], "Score must decay"
        assert result.iloc[2] < result.iloc[1], "Score must continue decaying"

if __name__ == "__main__":
    pytest.main([__file__])
