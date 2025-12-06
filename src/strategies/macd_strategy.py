from src.strategies.base import Strategy
import pandas as pd
import numpy as np

class MACDStrategy(Strategy):
    def __init__(self, params=None):
        super().__init__(params)
        self.fast = self.params.get('fast', 12)
        self.slow = self.params.get('slow', 26)
        self.signal_period = self.params.get('signal_period', 9)

    def ema(self, series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        self.data = data.copy()
        self.data.columns = [c.lower() for c in self.data.columns]
        
        close = self.data['close']
        ema_fast = self.ema(close, self.fast)
        ema_slow = self.ema(close, self.slow)
        macd = ema_fast - ema_slow
        signal_line = self.ema(macd, self.signal_period)
        
        self.data['macd'] = macd
        self.data['signal_line'] = signal_line
        
        prev_macd = macd.shift(1)
        prev_signal = signal_line.shift(1)
        
        self.data['entries'] = (macd > signal_line) & (prev_macd <= prev_signal)
        self.data['exits'] = (macd < signal_line) & (prev_macd >= prev_signal)
        
        return self.convert_to_signal(self.data)