import pandas as pd
import numpy as np

from src.strategies.base import Strategy
from src.config.settings import settings

class MovingAverageStrategy(Strategy):
    """
    Simple Moving Average Trend Following Strategy.
    Buy when Close > MA, Sell when Close < MA.
    """
    def __init__(self, window: int = settings.DEFAULT_MA_WINDOW):
        super().__init__()
        self.window = window

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        self.data = data.copy()
        # Ensure lowercase columns
        self.data.columns = [c.lower() for c in self.data.columns]
        
        if 'close' not in self.data.columns:
            raise ValueError("Data must contain a 'close' column.")
            
        # Use safe_rolling for MA (excludes current candle)
        self.data['ma'] = self.safe_rolling('close', self.window, 'mean')
        
        self.data['signal'] = 0
        # Buy signal (Trend Up)
        self.data.loc[self.data['close'] > self.data['ma'], 'signal'] = 1
        # Sell signal (Trend Down)
        self.data.loc[self.data['close'] < self.data['ma'], 'signal'] = -1
        
        # Clean up NaN
        self.data['signal'] = self.data['signal'].fillna(0)
        
        return self.data

class RSIStrategy(Strategy):
    """
    RSI Mean Reversion Strategy.
    Uses Wilder's Smoothing (Standard RSI).
    Buy when RSI < buy_threshold (oversold).
    Sell when RSI > sell_threshold (overbought).
    """
    def __init__(self, period: int = settings.DEFAULT_RSI_PERIOD, buy_threshold: int = settings.DEFAULT_RSI_BUY_THRESHOLD, sell_threshold: int = settings.DEFAULT_RSI_SELL_THRESHOLD):
        super().__init__()
        self.period = period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def _calculate_rsi(self, series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        
        # Separate gains and losses
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)

        # Use Exponential Moving Average (Wilder's Method)
        # com = period - 1 corresponds to alpha = 1 / period
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
        
        self.data['signal'] = 0
        # Buy (Oversold)
        self.data.loc[self.data['rsi'] < self.buy_threshold, 'signal'] = 1
        # Sell (Overbought)
        self.data.loc[self.data['rsi'] > self.sell_threshold, 'signal'] = -1
        
        self.data['signal'] = self.data['signal'].fillna(0.0)
        
        return self.data

class BollingerBreakoutStrategy(Strategy):
    """
    Bollinger Band Breakout Strategy.
    Buy when Close breaks above Upper Band.
    Sell when Close falls below Moving Average (Center Line).
    """
    def __init__(self, window: int = 20, std_dev: float = 2.0):
        super().__init__()
        self.window = window
        self.std_dev = std_dev

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        self.data = data.copy()
        self.data.columns = [c.lower() for c in self.data.columns]
        
        if 'close' not in self.data.columns:
            raise ValueError("Data must contain a 'close' column.")
            
        # Calculate Bands using safe_rolling
        self.data['ma'] = self.safe_rolling('close', self.window, 'mean')
        self.data['std'] = self.safe_rolling('close', self.window, 'std')
        self.data['upper'] = self.data['ma'] + (self.data['std'] * self.std_dev)

        
        self.data['signal'] = 0
        
        # Buy Signal: Breakout above Upper Band
        self.data.loc[self.data['close'] > self.data['upper'], 'signal'] = 1
        
        # Sell Signal: Trend reversal (Close below MA)
        self.data.loc[self.data['close'] < self.data['ma'], 'signal'] = -1
        
        self.data['signal'] = self.data['signal'].fillna(0)
        
        return self.data

PRESET_STRATEGIES = {
    "MovingAverageStrategy": MovingAverageStrategy,
    "RSIStrategy": RSIStrategy,
    "BollingerBreakoutStrategy": BollingerBreakoutStrategy
}
