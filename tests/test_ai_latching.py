
import pandas as pd
import numpy as np
import pytest
from src.strategies.base import Strategy

class LatchingStrategy(Strategy):
    """
    Mock AI Generated Strategy implementing State Latching.
    Follows the "Golden Template" logic to be enforced in prompts.
    """
    def __init__(self, params=None):
        super().__init__(params)
        self.ma_window = self.params.get('ma_window', 3)

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        self.data = data.copy()
        
        # 1. Indicators
        self.data['ma'] = self.data['close'].rolling(window=self.ma_window).mean()
        
        # 2. Define Triggers (Pulse Signals)
        # Entry: Close > MA
        buy_signal = (self.data['close'] > self.data['ma'])
        # Exit: Close < MA
        sell_signal = (self.data['close'] < self.data['ma'])

        # 3. Apply Logic
        self.data['signal'] = 0
        self.data.loc[buy_signal, 'signal'] = 1
        self.data.loc[sell_signal, 'signal'] = -1 

        # 4. Latch State (The Core Logic being tested)
        # Replace 0s with NaN so we can forward-fill the previous state
        self.data['signal'] = self.data['signal'].replace(0, np.nan).ffill().fillna(0)

        # 5. Enforce Long-Only for this test (Optional in general, but good for verification)
        # We want to ensure that once we sell (-1), we go to 0 (flat), not short.
        # But wait, the standard latch logic:
        # If I have 1 (Long), then 0 (Null), 0 (Null) -> ffill gives 1, 1.
        # Then I hit -1 (Sell).
        # Next 0 (Null) -> ffill gives -1.
        # So we usually want to replace -1 with 0 AFTER ffill? 
        # Or does the prompt say "Ensure -1 becomes 0 (Flat)"?
        # Let's check the prompt instruction: "Ensure -1 becomes 0 (Flat)"
        
        self.data['signal'] = self.data['signal'].replace(-1, 0)
        
        return self.data

def test_state_latching_logic():
    """
    Verifies that a signal is maintained (latched) between entry and exit.
    """
    # Create synthetic data
    # Day 0: NaN MA
    # Day 1: NaN MA
    # Day 2: MA=20 (10,20,30). Close=30. > MA. BUY (1).
    # Day 3: MA=30 (20,30,40). Close=35. > MA. BUY (1) - redundant but keeps state.
    # Day 4: MA=31.6 (30,40,25). Close=25. < MA. SELL (-1).
    # Day 5: MA=25 (40,25,10). Close=10. < MA. SELL (-1) - redundant.
    # Day 6: MA=16.6 (25,10,15). Close=15. < MA. SELL (-1).
    # Day 7: MA=13.3 (10,15,15). Close=15. > MA. BUY (1).
    # Day 8: MA=15 (15,15,15). Close=15. = MA. No Trigger (0). Should Hold (1).
    
    prices = [10, 20, 30, 40, 25, 10, 15, 15, 15] 
    # MAs (3-day):
    # 0: NaN
    # 1: NaN
    # 2: (10+20+30)/3 = 20. Close 30 > 20 -> BUY.
    # 3: (20+30+40)/3 = 30. Close 40 > 30 -> BUY (Pulse 1).
    # 4: (30+40+25)/3 = 31.6. Close 25 < 31.6 -> SELL (Pulse -1).
    # 5: (40+25+10)/3 = 25. Close 10 < 25 -> SELL (Pulse -1).
    # 6: (25+10+15)/3 = 16.6. Close 15 < 16.6 -> SELL (Pulse -1).
    # 7: (10+15+15)/3 = 13.3. Close 15 > 13.3 -> BUY (Pulse 1).
    # 8: (15+15+15)/3 = 15. Close 15 == 15. NO TRIGGER (Pulse 0).
    
    # Expected Latch Behavior:
    # 2: 1
    # 3: 1
    # 4: -1 -> 0
    # 5: -1 -> 0
    # 6: -1 -> 0
    # 7: 1
    # 8: 1 (Latched from 7)
    
    df = pd.DataFrame({'close': prices})
    
    strategy = LatchingStrategy({'ma_window': 3})
    results = strategy.generate_signals(df)
    
    print(results[['close', 'ma', 'signal']])
    
    # Check Day 2 (First Buy)
    assert results.loc[2, 'signal'] == 1.0, "Day 2 should be a BUY signal"
    
    # Check Day 4 (First Sell)
    # The raw signal is -1. The prompt logic replaces -1 with 0 (Flat).
    assert results.loc[4, 'signal'] == 0.0, "Day 4 should be FLAT (Sold)"
    
    # Check Day 7 (Second Buy)
    assert results.loc[7, 'signal'] == 1.0, "Day 7 should be a BUY signal"
    
    # Check Day 8 (Latch Test)
    # Day 8 has Close=15, MA=15. It is NOT > MA, so raw pulse is 0.
    # But Day 7 was 1. ffill() should make Day 8 = 1.
    assert results.loc[8, 'signal'] == 1.0, "Day 8 should be LATCHED to 1 (Holding)"

if __name__ == "__main__":
    test_state_latching_logic()
