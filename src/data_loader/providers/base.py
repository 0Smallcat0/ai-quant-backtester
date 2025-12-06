from abc import ABC, abstractmethod
import pandas as pd

class BaseDataProvider(ABC):
    """Abstract base class for data providers."""

    @abstractmethod
    def fetch_history(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical data for a given ticker.

        Args:
            ticker (str): The symbol to fetch.
            start_date (str): Start date in 'YYYY-MM-DD' format.
            end_date (str): End date in 'YYYY-MM-DD' format.

        Returns:
            pd.DataFrame: DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Volume']
                          and DatetimeIndex.
        """
        pass
