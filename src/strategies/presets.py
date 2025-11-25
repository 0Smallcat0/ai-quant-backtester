import pandas as pd

from src.strategies.base import Strategy
from src.config.settings import (
    DEFAULT_MA_WINDOW, DEFAULT_RSI_PERIOD, 
    DEFAULT_RSI_BUY_THRESHOLD, DEFAULT_RSI_SELL_THRESHOLD
)

class MovingAverageStrategy(Strategy):
    """
    Simple Moving Average Trend Following Strategy.
    Buy when Close > MA, Sell when Close < MA.
    """
    def __init__(self, window: int = DEFAULT_MA_WINDOW):
        self.window = window

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        # Ensure lowercase columns
        df.columns = [c.lower() for c in df.columns]
        
        if 'close' not in df.columns:
            raise ValueError("Data must contain a 'close' column.")
            
        df['ma'] = df['close'].rolling(window=self.window).mean()
        
        df['signal'] = 0
        # Buy signal (Trend Up)
        df.loc[df['close'] > df['ma'], 'signal'] = 1
        # Sell signal (Trend Down)
        df.loc[df['close'] < df['ma'], 'signal'] = -1
        
        # Clean up NaN
        df['signal'] = df['signal'].fillna(0)
        
        return df

class RSIStrategy(Strategy):
    """
    RSI Mean Reversion Strategy.
    Uses Wilder's Smoothing (Standard RSI).
    Buy when RSI < buy_threshold (oversold).
    Sell when RSI > sell_threshold (overbought).
    """
    def __init__(self, period: int = DEFAULT_RSI_PERIOD, buy_threshold: int = DEFAULT_RSI_BUY_THRESHOLD, sell_threshold: int = DEFAULT_RSI_SELL_THRESHOLD):
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
        df = data.copy()
        df.columns = [c.lower() for c in df.columns]
        
        if 'close' not in df.columns:
            raise ValueError("Data must contain a 'close' column.")
            
        df['rsi'] = self._calculate_rsi(df['close'], self.period)
        
        df['signal'] = 0
        # Buy (Oversold)
        df.loc[df['rsi'] < self.buy_threshold, 'signal'] = 1
        # Sell (Overbought)
        df.loc[df['rsi'] > self.sell_threshold, 'signal'] = -1
        
        df['signal'] = df['signal'].fillna(0.0)
        
        return df

class BollingerBreakoutStrategy(Strategy):
    """
    Bollinger Band Breakout Strategy.
    Buy when Close breaks above Upper Band.
    Sell when Close falls below Moving Average (Center Line).
    """
    def __init__(self, window: int = 20, std_dev: float = 2.0):
        self.window = window
        self.std_dev = std_dev

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df.columns = [c.lower() for c in df.columns]
        
        if 'close' not in df.columns:
            raise ValueError("Data must contain a 'close' column.")
            
        # Calculate Bands
        df['ma'] = df['close'].rolling(window=self.window).mean()
        df['std'] = df['close'].rolling(window=self.window).std()
        df['upper'] = df['ma'] + (df['std'] * self.std_dev)

        
        df['signal'] = 0
        
        # Buy Signal: Breakout above Upper Band
        df.loc[df['close'] > df['upper'], 'signal'] = 1
        
        # Sell Signal: Trend reversal (Close below MA)
        df.loc[df['close'] < df['ma'], 'signal'] = -1
        
        df['signal'] = df['signal'].fillna(0)
        
        return df

PRESET_STRATEGIES = {
    "MovingAverageStrategy": MovingAverageStrategy,
    "RSIStrategy": RSIStrategy,
    "BollingerBreakoutStrategy": BollingerBreakoutStrategy
}
