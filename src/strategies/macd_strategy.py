from strategies.base import Strategy
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
        data = data.copy()
        data.columns = [c.lower() for c in data.columns]
        
        ema_fast = self.ema(data['close'], self.fast)
        ema_slow = self.ema(data['close'], self.slow)
        macd_line = ema_fast - ema_slow
        signal_line = self.ema(macd_line, self.signal_period)
        
        data['macd'] = macd_line
        data['signal_line'] = signal_line
        data['prev_macd'] = macd_line.shift(1)
        data['prev_signal'] = signal_line.shift(1)
        
        data['signal'] = 0
        # 向上突破買入
        buy_condition = (data['macd'] > data['signal_line']) & (data['prev_macd'] <= data['prev_signal'])
        data.loc[buy_condition, 'signal'] = 1
        # 向下突破賣出
        sell_condition = (data['macd'] < data['signal_line']) & (data['prev_macd'] >= data['prev_signal'])
        data.loc[sell_condition, 'signal'] = -1
        
        return data