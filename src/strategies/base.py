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
