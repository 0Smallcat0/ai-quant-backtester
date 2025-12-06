from src.strategies.base import Strategy
import pandas as pd
import numpy as np

class MockThinStrategy(Strategy):
    """
    Mock Strategy following the new 'Thin Prompt' protocol.
    Outputs 'entries' and 'exits' instead of 'signal'.
    """
    def __init__(self, params=None):
        super().__init__(params)

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        self.data = data.copy()
        self.data.columns = [c.lower() for c in self.data.columns]
        
        # Create Dummy Data for determinism
        # T1: Flat
        # T2: Entry -> True
        # T3: Flat
        # T4: Exit -> True
        # T5: Flat
        
        # We need to rely on the index of the passed data
        n = len(self.data)
        
        # Init
        self.data['entries'] = False
        self.data['exits'] = False
        
        if n >= 5:
            # We set specific rows if possible, or just use modular arithmetic for robustness
            self.data.iloc[1, self.data.columns.get_loc('entries')] = True # T2 Entry
            self.data.iloc[3, self.data.columns.get_loc('exits')] = True   # T4 Exit
            
        return self.data
