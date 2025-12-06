from abc import ABC, abstractmethod
import pandas as pd
import numpy as np

class Strategy(ABC):
    def __init__(self, params: dict = None):
        self.params = params or {}

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        pass

    def convert_to_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'entries' in df.columns and 'exits' in df.columns:
            df['signal'] = 0
            df.loc[df['entries'], 'signal'] = 1
            df.loc[df['exits'], 'signal'] = -1
        elif 'signal' not in df.columns:
             df['signal'] = 0
        return df

    def safe_rolling(self, column: str, window: int, func: str = 'mean') -> pd.Series:
        if not hasattr(self, 'data') or self.data is None:
             raise ValueError("Strategy data not initialized")
        return self.data[column].shift(1).rolling(window=window).agg(func)

    def safe_pct_change(self, column: str, periods: int = 1) -> pd.Series:
        if not hasattr(self, 'data') or self.data is None:
             raise ValueError("Strategy data not initialized")
        return self.data[column].shift(1).pct_change(periods=periods)
