import traceback
import re
from src.strategies.base import Strategy

class StrategyLoadError(Exception):
    """Custom exception for errors during strategy loading."""
    pass

class StrategyLoader:
    """
    Responsible for dynamically loading strategy classes from code strings.
    """

    def load_from_code(self, code_str: str) -> Strategy:
        """
        Executes the provided code string and returns an instance of the Strategy class defined within.

        Args:
            code_str (str): The Python code string containing the strategy class.

        Returns:
            Strategy: An instance of the loaded strategy.

        Raises:
            StrategyLoadError: If the code is invalid, no Strategy class is found, or instantiation fails.
        """
        namespace = {}
        
        # Static Analysis for Look-ahead Bias
        # Security Check: Look-ahead Bias Detection using Regex
        # We check for negative shifts and forward indexing which imply future data access.
        forbidden_regexes = [
            r"\.shift\s*\(\s*-",      # Matches .shift(-1), .shift( -1 ), etc.
            r"shift\s*\(\s*-",        # Variant without dot
            r"\.iloc\s*\[\s*i\s*\+\s*\d+",  # Matches .iloc[i+1], .iloc[ i + 1 ], etc.
            r"\.iloc\s*\[\s*:\s*-?\d+",  # .iloc[:-5] Slicing lookahead
            r"shift\s*\(\s*-?\d+\s*\)",  # shift(-1)
            r"\.iloc\s*\[\s*i\s*\+\s*\d+", # .iloc[i+1] Future index
            r"\.iloc\s*\[\s*\d+\s*:"     # .iloc[10:] Future slice
        ]
        
        for pattern in forbidden_regexes:
            if re.search(pattern, code_str):
                raise StrategyLoadError(f"Security Violation: Detected potential look-ahead bias pattern '{pattern}'. Future data access is forbidden.")

        try:
            # Execute the code in a restricted namespace
            # We use the same dictionary for globals and locals to ensure imports are visible
            # to class definitions (e.g. for type hints)
            exec(code_str, namespace)
        except SyntaxError as e:
            raise StrategyLoadError(f"Syntax Error in strategy code: {e}")
        except Exception as e:
            raise StrategyLoadError(f"Error executing strategy code: {e}\n{traceback.format_exc()}")

        # Find the class that inherits from Strategy
        strategy_class = None
        for name, obj in namespace.items():
            if isinstance(obj, type) and issubclass(obj, Strategy) and obj is not Strategy:
                strategy_class = obj
                break
        
        if not strategy_class:
            raise StrategyLoadError("No class inheriting from 'Strategy' found in the provided code.")

        # Verify that the class implements the required interface
        # Although ABC enforces this at instantiation, we can check explicitly for clarity
        if not hasattr(strategy_class, 'generate_signals'):
             raise StrategyLoadError(f"Strategy class '{strategy_class.__name__}' must implement 'generate_signals' method.")

        try:
            return strategy_class(params={})
        except Exception as e:
            raise StrategyLoadError(f"Error instantiating strategy class '{strategy_class.__name__}': {e}")

    def load_preset(self, strategy_name: str, **kwargs) -> Strategy:
        """
        Loads a preset strategy by name.

        Args:
            strategy_name (str): The name of the strategy class (e.g., 'MovingAverageStrategy').
            **kwargs: Arguments to pass to the strategy constructor.

        Returns:
            Strategy: An instance of the loaded strategy.
        """
        import src.strategies.presets as presets
        
        if not hasattr(presets, strategy_name):
             raise StrategyLoadError(f"Preset strategy '{strategy_name}' not found.")
             
        strategy_class = getattr(presets, strategy_name)
        try:
            return strategy_class(**kwargs)
        except Exception as e:
            raise StrategyLoadError(f"Error instantiating preset '{strategy_name}': {e}")