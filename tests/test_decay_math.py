import pytest
import pandas as pd
import numpy as np
from src.data.sentiment_processor import DecayModel

class TestDecayMath:
    def test_stability_at_one(self):
        """
        Case 1: Input continuous 1.0 scores. 
        Expected: Output should stabilize at 1.0 and NOT exceed it.
        """
        # Setup
        dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
        raw_scores = {d: 1.0 for d in dates}
        
        # Initialize model with a reasonable half-life (e.g., 5 days)
        model = DecayModel(half_life_days=5.0)
        
        # Execute
        result = model.apply_decay(dates, raw_scores)
        
        # Verify
        # The first value should be 1.0
        assert result.iloc[0] == 1.0, "Initial value should be 1.0"
        
        # Check for runaway growth (Old bug: values > 1.0)
        max_score = result.max()
        assert max_score <= 1.000001, f"Score exceeded 1.0! Max detected: {max_score}"
        
        # Ideally, it should stay exactly 1.0 if the formula is correct:
        # 1*d + 1*(1-d) = 1
        assert np.allclose(result.values, 1.0), f"Scores diverged from 1.0: {result.values}"

    def test_decay_behavior(self):
        """
        Case 2: Input 1.0 then silence (0.0 or missing).
        Expected: Score should decay towards 0.
        """
        # Setup
        dates = pd.date_range(start='2023-01-01', periods=6, freq='D')
        # Day 1: 1.0, subsequent days: no news (effectively 0.0 input for the new term)
        raw_scores = {dates[0]: 1.0}
        
        model = DecayModel(half_life_days=2.0) # Fast decay for testing
        
        # Execute
        result = model.apply_decay(dates, raw_scores)
        
        # Verify
        first_val = result.iloc[0]
        last_val = result.iloc[-1]
        
        assert first_val == 1.0
        assert last_val < first_val, "Score did not decay"
        assert last_val > 0.0, "Score should not reach exactly zero immediately"
        
        # Check math roughly:
        # t=0: 1.0
        # t=1: 1.0 * exp(-ln(2)/2 * 1) = 1.0 * 0.707...
        # New input is 0. So S_t = S_{t-1}*d + 0*(1-d) = S_{t-1}*d
        expected_decay_factor = np.exp(-np.log(2)/2) 
        expected_t1 = 1.0 * expected_decay_factor
        assert np.isclose(result.iloc[1], expected_t1, atol=0.01), f"Decay step 1 inconsistent. Got {result.iloc[1]}, expected {expected_t1}"

    def test_clamping(self):
        """
        Ensure inputs > 1.0 are clamped before processing.
        """
        dates = pd.date_range(start='2023-01-01', periods=1, freq='D')
        raw_scores = {dates[0]: 5.0} # Way out of bounds
        
        model = DecayModel(half_life_days=5.0)
        result = model.apply_decay(dates, raw_scores)
        
        assert result.iloc[0] == 1.0, f"Input 5.0 was not clamped to 1.0, got {result.iloc[0]}"

    def test_steady_state_value(self):
        """
        Case 3: Input continuous 0.5 scores.
        Current Bug: 0.5 + 0.5 + ... grows to 1.0.
        Correct EWMA: Should stabilize at 0.5.
        """
        dates = pd.date_range(start='2023-01-01', periods=20, freq='D')
        raw_scores = {d: 0.5 for d in dates}
        
        # Half life 5 days -> decay factor ~0.87
        model = DecayModel(half_life_days=5.0)
        result = model.apply_decay(dates, raw_scores)
        
        # In the buggy additive model:
        # t=0: 0.5
        # t=1: 0.5*0.87 + 0.5 = 0.935
        # t=2: 0.935*0.87 + 0.5 = 1.31 -> clamped 1.0
        # So it will be 1.0.
        
        # In EWMA:
        # t=0: 0.5
        # t=1: 0.5*0.87 + 0.5*(1-0.87) = 0.5
        # Should stay 0.5.
        
        last_val = result.iloc[-1]
        assert abs(last_val - 0.5) < 0.05, f"Score drifted from 0.5! Got {last_val}"

