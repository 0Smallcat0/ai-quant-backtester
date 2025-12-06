import pytest
import pandas as pd
import numpy as np
import sys
import os

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.backtest.thick_engine import apply_latching_engine, fast_signal_latch_nb

class TestThickEngine:
    
    def test_basic_latching(self):
        """
        Verify basic latching logic:
        T1: Entry -> Position=True
        T2: No Signal -> Position=True (Latched)
        T3: Exit -> Position=False
        """
        entries = pd.Series([False, True, False, False, False])
        exits   = pd.Series([False, False, False, True, False])
        
        # Expected: F, T, T, F, F
        # Note: T4 Exit is True, so T4 becomes False (Flat) immediately if we follow "Market On Close" or "Signal impacts T"
        # Our logic: 
        # T1 (F,F) -> F
        # T2 (Entry) -> T
        # T3 (None) -> T (Latch)
        # T4 (Exit) -> F
        # T5 (None) -> F
        
        result = apply_latching_engine(entries, exits)
        expected = np.array([False, True, True, False, False])
        
        np.testing.assert_array_equal(result.values, expected)

    def test_conflict_resolution(self):
        """
        Test simultaneous Entry and Exit.
        Logic dictates: If in position, Exit takes precedence. If flat, Entry takes precedence.
        """
        # Case 1: Flat -> Entry + Exit same day.
        # Should Entry trigger? Or Exit cancel it?
        # Logic: if current=False: check Entry -> True.
        # Wait, the loop is:
        # if current: check Exit -> False
        # else: check Entry -> True
        # So if Flat, and both True:
        # else branch runs -> current becomes True. (Entry wins if Flat)
        
        entries = np.array([True], dtype=bool)
        exits = np.array([True], dtype=bool)
        
        # Initial False
        # -> Else branch -> inputs True -> current becomes True
        res = fast_signal_latch_nb(entries, exits, initial_state=False)
        assert res[0] == True
        
        # Case 2: In Position -> Entry + Exit same day.
        # if current(True): check Exit -> True -> current becomes False.
        # Entry is ignored.
        res_held = fast_signal_latch_nb(entries, exits, initial_state=True)
        assert res_held[0] == False

    def test_dataframe_support(self):
        """Test multi-asset DataFrame support."""
        idx = pd.date_range('2023-01-01', periods=3)
        entries = pd.DataFrame({
            'A': [True, False, False],
            'B': [False, True, False]
        }, index=idx)
        
        exits = pd.DataFrame({
            'A': [False, False, True],
            'B': [False, False, False]
        }, index=idx)
        
        result = apply_latching_engine(entries, exits)
        
        # A: T, T, F
        np.testing.assert_array_equal(result['A'].values, [True, True, False])
        # B: F, T, T
        np.testing.assert_array_equal(result['B'].values, [False, True, True])

    def test_lookahead_prevention(self):
        """Verify errors are raised for mismatched indexes."""
        e = pd.Series([True], index=[0])
        x = pd.Series([True], index=[1])
        with pytest.raises(ValueError):
            apply_latching_engine(e, x)
