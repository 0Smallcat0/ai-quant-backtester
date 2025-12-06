import pandas as pd
import numpy as np

from src.strategies.base import Strategy
from src.config.settings import settings
from src.strategies.sizing import SentimentSizer

class MovingAverageStrategy(Strategy):
    def __init__(self, window: int = settings.DEFAULT_MA_WINDOW):
        super().__init__()
        self.window = window

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        self.data = data.copy()
        self.data.columns = [c.lower() for c in self.data.columns]
        
        if 'close' not in self.data.columns:
            raise ValueError("Data must contain a 'close' column.")
            
        self.data['ma'] = self.safe_rolling('close', self.window, 'mean')
        
        self.data['entries'] = self.data['close'] > self.data['ma']
        self.data['exits'] = self.data['close'] < self.data['ma']
        
        return self.convert_to_signal(self.data)

class SentimentRSIStrategy(Strategy):
    def __init__(self, period: int = settings.DEFAULT_RSI_PERIOD, buy_threshold: int = settings.DEFAULT_RSI_BUY_THRESHOLD, sell_threshold: int = settings.DEFAULT_RSI_SELL_THRESHOLD, sentiment_threshold: float = 0.0, use_dynamic_sizing: bool = True):
        super().__init__()
        self.period = period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.sentiment_threshold = sentiment_threshold
        self.name = "SentimentRSI"
        self.use_dynamic_sizing = use_dynamic_sizing
        self.sizer = SentimentSizer(min_sentiment_threshold=sentiment_threshold)

    def _calculate_rsi(self, series: pd.Series, period: int) -> pd.Series:
        delta = series.shift(1).diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)

        avg_gain = gain.ewm(com=period-1, adjust=False).mean()
        avg_loss = loss.ewm(com=period-1, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        self.data = data.copy()
        self.data.columns = [c.lower() for c in self.data.columns]
        
        if 'close' not in self.data.columns:
            raise ValueError("Data must contain a 'close' column.")
            
        self.data['rsi'] = self._calculate_rsi(self.data['close'], self.period)
        
        if 'sentiment' not in self.data.columns:
            self.data['sentiment'] = 0.0
        
        self.data['entries'] = (self.data['rsi'] < self.buy_threshold) & (self.data['sentiment'] >= self.sentiment_threshold)
        self.data['exits'] = self.data['rsi'] > self.sell_threshold

        if self.use_dynamic_sizing:
            # [OPTIMIZATION] Vectorized call
            self.data['target_size'] = self.sizer.get_target_weight(self.data['sentiment'])
        else:
            self.data['target_size'] = 1.0

        return self.convert_to_signal(self.data)

class BollingerBreakoutStrategy(Strategy):
    def __init__(self, window: int = 20, std_dev: float = 2.0):
        super().__init__()
        self.window = window
        self.std_dev = std_dev

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        self.data = data.copy()
        self.data.columns = [c.lower() for c in self.data.columns]
        
        if 'close' not in self.data.columns:
            raise ValueError("Data must contain a 'close' column.")
            
        self.data['ma'] = self.safe_rolling('close', self.window, 'mean')
        self.data['std'] = self.safe_rolling('close', self.window, 'std')
        self.data['upper'] = self.data['ma'] + (self.data['std'] * self.std_dev)

        self.data['entries'] = self.data['close'] > self.data['upper']
        self.data['exits'] = self.data['close'] < self.data['ma']
        
        return self.convert_to_signal(self.data)

PRESET_STRATEGIES = {
    "MovingAverageStrategy": MovingAverageStrategy,
    "SentimentRSIStrategy": SentimentRSIStrategy,
    "BollingerBreakoutStrategy": BollingerBreakoutStrategy
}
