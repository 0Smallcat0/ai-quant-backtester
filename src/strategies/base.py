from abc import ABC, abstractmethod
import pandas as pd

class Strategy(ABC):
    """
    Abstract Base Class for all strategies.
    """

    def __init__(self, params: dict = None):
        """
        Initialize the strategy with parameters.
        
        Args:
            params (dict, optional): Strategy parameters. Defaults to None.
        """
        self.params = params or {}

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generates trading signals based on the input data.
        
        Args:
            data (pd.DataFrame): Historical market data.
            
        Returns:
            pd.DataFrame: Data with a 'signal' column (1 for buy, -1 for sell, 0 for hold).
        """
        pass

    def safe_rolling(self, column: str, window: int, func: str = 'mean') -> pd.Series:
        """
        Calculates a rolling window statistic safely by shifting data first.
        This ensures that the calculation at time T only uses data from T-1 and earlier.
        
        Args:
            column (str): Column name to calculate on (e.g., 'close').
            window (int): Size of the rolling window.
            func (str): Aggregation function ('mean', 'std', 'max', 'min', etc.).
            
        Returns:
            pd.Series: The calculated rolling series.
        """
        if not hasattr(self, 'data') or self.data is None:
             raise ValueError("Strategy data not initialized. Ensure 'self.data' is set before calling helpers.")
             
        # Shift by 1 to exclude current day's data from the window
        # e.g. At T, we want Rolling(Window) of [T-1, T-2, ...]
        return self.data[column].shift(1).rolling(window=window).agg(func)

    def safe_pct_change(self, column: str, periods: int = 1) -> pd.Series:
        """
        Calculates percentage change safely by shifting data first.
        
        Args:
            column (str): Column name.
            periods (int): Number of periods to shift.
            
        Returns:
            pd.Series: The percentage change series.
        """
        if not hasattr(self, 'data') or self.data is None:
             raise ValueError("Strategy data not initialized.")
             
        return self.data[column].shift(1).pct_change(periods=periods)
