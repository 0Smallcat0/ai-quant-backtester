import traceback
import re
from src.strategies.base import Strategy
from src.config.settings import settings

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
        # We check for negative shifts and forward indexing which imply future data access.
        forbidden_regexes = settings.FORBIDDEN_REGEXES
        
        for pattern in forbidden_regexes:
            if re.search(pattern, code_str):
                raise StrategyLoadError(f"Security Violation: Detected potential look-ahead bias pattern '{pattern}'. Future data access is forbidden.")

        try:
            # Execute the code in a restricted namespace
            # We use the same dictionary for globals and locals to ensure imports are visible
            # to class definitions (e.g. for type hints)
            exec(code_str, namespace)
        except SyntaxError as e:
            # Check for potential truncation (simple heuristic: end of string/file)
            error_msg = str(e)
            if "unexpected EOF" in error_msg or "unterminated string literal" in error_msg:
                 raise StrategyLoadError(f"Strategy Load Error: AI response was truncated (SyntaxError: {e}). Please try again with a simpler request.")
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
            import inspect
            # Check strategy signature
            sig = inspect.signature(strategy_class.__init__)
            params = {} # Default params for now

            if 'params' in sig.parameters:
                # Case A: Standard Pattern (supports params dict)
                return strategy_class(params=params)
            else:
                # Case B: Legacy/Preset Pattern (supports named args)
                # Filter params to match signature to avoid TypeError
                # Since we are loading from code without user input params here, we depend on defaults.
                # If we had kwargs, we would pass them here.
                valid_params = {k: v for k, v in params.items() if k in sig.parameters}
                return strategy_class(**valid_params)

        except Exception as e:
            raise StrategyLoadError(f"Error instantiating strategy class '{strategy_class.__name__}': {e}")

    def _camel_to_snake(self, name: str) -> str:
        """Converts CamelCase to snake_case."""
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

    def load_strategy(self, strategy_name: str) -> type:
        """
        Loads a strategy class by name.
        
        Priority:
        1. Presets (src.strategies.presets)
        2. Dynamic File Discovery (src/strategies/{snake_case_name}.py)
        
        Args:
            strategy_name (str): Name of the strategy class.
            
        Returns:
            type: The strategy class (subclass of Strategy).
            
        Raises:
            StrategyLoadError: If strategy cannot be found or loaded.
        """
        # 1. Check Presets
        import src.strategies.presets as presets
        if hasattr(presets, strategy_name):
            return getattr(presets, strategy_name)

        # 2. Dynamic File Discovery
        import os
        import importlib.util
        
        filename = self._camel_to_snake(strategy_name) + ".py"
        strategies_dir = os.path.dirname(__file__)
        file_path = os.path.join(strategies_dir, filename)
        
        if os.path.exists(file_path):
            try:
                spec = importlib.util.spec_from_file_location(strategy_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # [FIX] Smart Class Extraction
                    # Instead of looking for exact name match, find the first Strategy subclass
                    import inspect
                    
                    target_class = None
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        # [DEBUG] Inspecting class
                        # print(f"DEBUG: Checking class: {name}, Base: {obj.__bases__}, Module: {obj.__module__}")
                        
                        # Check if it's a Strategy subclass, not Strategy itself, and defined in this module
                        # [FIX] Handle Import Path Hell: Check name of base class if issubclass fails
                        is_strategy_subclass = False
                        try:
                            if issubclass(obj, Strategy):
                                is_strategy_subclass = True
                        except TypeError:
                            pass # issubclass might fail if obj is not a class (but we checked isclass)
                        
                        if not is_strategy_subclass:
                            # Fallback: Check base class names
                            for base in obj.__bases__:
                                if base.__name__ == 'Strategy':
                                    is_strategy_subclass = True
                                    break
                        
                        if is_strategy_subclass and obj.__name__ != 'Strategy' and obj.__module__ == module.__name__:
                            target_class = obj
                            break
                    
                    if target_class:
                        return target_class
                    
                    # Fallback: Check if the strategy_name exists exactly (legacy behavior)
                    if hasattr(module, strategy_name):
                        strategy_class = getattr(module, strategy_name)
                        
                        is_strategy_subclass = False
                        try:
                            if issubclass(strategy_class, Strategy):
                                is_strategy_subclass = True
                        except TypeError:
                            pass
                            
                        if not is_strategy_subclass:
                             for base in strategy_class.__bases__:
                                if base.__name__ == 'Strategy':
                                    is_strategy_subclass = True
                                    break
                        
                        if is_strategy_subclass and strategy_class.__name__ != 'Strategy':
                            return strategy_class
            except Exception as e:
                 print(f"CRITICAL ERROR loading module: {e}")
                 import traceback
                 traceback.print_exc()
                 raise StrategyLoadError(f"Error loading strategy file '{filename}': {e}")

        raise StrategyLoadError(f"Strategy '{strategy_name}' not found in presets or as a file.")

    def load_preset(self, strategy_name: str, **kwargs) -> Strategy:
        """
        Loads a preset strategy by name.
        DEPRECATED: Use load_strategy instead.
        """
        strategy_class = self.load_strategy(strategy_name)
        try:
            import inspect
            sig = inspect.signature(strategy_class.__init__)
            
            if 'params' in sig.parameters:
                # Case A: Standard Pattern (supports params dict)
                # If kwargs are passed, wrap them in params dict
                return strategy_class(params=kwargs)
            else:
                # Case B: Legacy/Preset Pattern (supports named args)
                # Filter kwargs to match signature
                valid_params = {k: v for k, v in kwargs.items() if k in sig.parameters}
                return strategy_class(**valid_params)
        except Exception as e:
            raise StrategyLoadError(f"Error instantiating preset '{strategy_name}': {e}")