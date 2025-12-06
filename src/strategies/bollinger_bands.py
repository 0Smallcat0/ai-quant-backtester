from src.strategies.base import Strategy
import pandas as pd
import numpy as np

class BollingerBandsStrategy(Strategy):
    def __init__(self, params=None):
        super().__init__(params)
        self.period = self.params.get('period', 20)
        self.mult = self.params.get('mult', 2.0)

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        self.data = data.copy()
        self.data.columns = [c.lower() for c in self.data.columns]
        
        if 'sentiment' not in self.data.columns:
            self.data['sentiment'] = 0.0
        self.data['sentiment'] = self.data['sentiment'].fillna(0.0)
        
        self.data['ma'] = self.safe_rolling('close', self.period, 'mean')
        self.data['std'] = self.safe_rolling('close', self.period, 'std')
        self.data['upper'] = self.data['ma'] + self.mult * self.data['std']
        self.data['lower'] = self.data['ma'] - self.mult * self.data['std']
        
        self.data['entries'] = (self.data['close'] <= self.data['lower'])
        self.data['exits'] = (self.data['close'] >= self.data['upper'])

        return self.data