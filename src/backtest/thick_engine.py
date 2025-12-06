import pandas as pd
import numpy as np
from numba import njit

@njit
def fast_signal_latch_nb(entries, exits, initial_state=False):
    """
    Numba compiled High-Performance State Machine: Resolves conflict between Trigger Signals and State Signals.
    
    Logic:
    - If current state is Flat (State=False):
        - Check Entry Signal. If True -> Switch to Position (State=True).
        - Ignore Exit Signal (cannot exit if flat).
    - If current state is Short/Long (State=True):
        - Check Exit Signal. If True -> Switch to Flat (State=False).
        - Ignore Entry Signal (Latch: already in position).
        
    Args:
        entries (bool array): Entry trigger signals.
        exits (bool array): Exit trigger signals.
        initial_state (bool): Initial position state.
        
    Returns:
        bool array: Continuous position state array.
    """
    n = entries.shape[0]
    position_mask = np.empty(n, dtype=np.bool_)
    current_state = initial_state

    for i in range(n):
        if current_state:
            # In Position: Check for Exit first
            if exits[i]:
                current_state = False
            # Latching: If not exiting, we stay in position regardless of new entries
        else:
            # Flat: Check for Entry
            if entries[i]:
                current_state = True
        
        position_mask[i] = current_state

    return position_mask

def apply_latching_engine(entries_df: pd.DataFrame, exits_df: pd.DataFrame) -> pd.DataFrame:
    """
    Wrapper to apply the Numba Core to Pandas DataFrames.
    Supports both Single Asset (Series) and Multi-Asset (DataFrame) processing.
    
    Args:
        entries_df (pd.DataFrame or pd.Series): Boolean Entry Triggers.
        exits_df (pd.DataFrame or pd.Series): Boolean Exit Triggers.
        
    Returns:
        pd.DataFrame or pd.Series: Boolean Position State (True=Holding, False=Flat).
    """
    # Defensive checks
    if hasattr(entries_df, 'index') and hasattr(exits_df, 'index'):
        if not entries_df.index.equals(exits_df.index):
            raise ValueError("Entry and Exit indexes must match to avoid lookahead bias.")

    # Convert to numpy for Numba
    # Handle Series vs DataFrame
    if isinstance(entries_df, pd.Series):
        entries_arr = entries_df.values
        exits_arr = exits_df.values
        
        # Ensure boolean
        entries_arr = entries_arr.astype(bool)
        exits_arr = exits_arr.astype(bool)
        
        out = fast_signal_latch_nb(entries_arr, exits_arr)
        return pd.Series(out, index=entries_df.index, name='position_state')
        
    elif isinstance(entries_df, pd.DataFrame):
        entries_arr = entries_df.values
        exits_arr = exits_df.values
        
        cols = entries_df.shape[1]
        out = np.empty_like(entries_arr, dtype=bool)
        
        # Determine column structure
        # If exits is a Series (common stop loss), broadcast it? 
        # For now assume 1:1 mapping strictly
        
        for c in range(cols):
            # Extract column c, ensure boolean
            e_col = entries_arr[:, c].astype(bool)
            x_col = exits_arr[:, c].astype(bool)
            out[:, c] = fast_signal_latch_nb(e_col, x_col)
            
        return pd.DataFrame(out, index=entries_df.index, columns=entries_df.columns)
    
    else:
        raise TypeError("Input must be Pandas Series or DataFrame")
