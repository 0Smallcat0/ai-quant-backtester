import argparse
import sys
import json
import pandas as pd
from datetime import datetime
import os

# Add src to python path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_engine import DataManager
from src.strategies.loader import StrategyLoader
from src.backtest_engine import BacktestEngine
from src.strategies.presets import PRESET_STRATEGIES
from config.settings import DB_PATH

def main():
    parser = argparse.ArgumentParser(description="Run a backtest for a specific strategy.")
    parser.add_argument("--strategy_name", required=True, help="Name of the strategy class")
    parser.add_argument("--ticker", default="BTC-USD", help="Ticker symbol (default: BTC-USD)")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--params", help="JSON string of strategy params")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    
    args = parser.parse_args()
    
    # [FIX] Sanitize arguments by stripping quotes
    if args.ticker:
        args.ticker = args.ticker.strip("'").strip('"')
    if args.strategy_name:
        args.strategy_name = args.strategy_name.strip("'").strip('"')
    if args.start:
        args.start = args.start.strip("'").strip('"')
    if args.end:
        args.end = args.end.strip("'").strip('"')
    
    # Parse params
    strategy_params = {}
    if args.params:
        try:
            # Handle potential double quotes issues from shell
            cleaned_params = args.params.strip("'").strip('"')
            strategy_params = json.loads(cleaned_params)
        except json.JSONDecodeError as e:
            print(f"Error parsing params JSON: {e}", file=sys.stderr)
            sys.exit(1)
    
    # [FIX] Ensure root dir AND src dir are in sys.path
    current_dir = os.path.dirname(os.path.abspath(__file__)) # src
    root_dir = os.path.dirname(current_dir) # root
    
    # Allow 'import src.strategies...'
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
        
    # Allow 'import strategies...' (Fix for "Import Path Hell")
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    try:
        # 1. Load Data
        data_manager = DataManager(db_path=str(DB_PATH))
        df = data_manager.get_data(args.ticker)
        
        if df.empty:
            raise ValueError(f"No data found for ticker {args.ticker}")
            
        # Filter by date if provided
        if args.start:
            df = df[df.index >= args.start]
        if args.end:
            df = df[df.index <= args.end]
            
        if df.empty:
            raise ValueError(f"No data found for ticker {args.ticker} in the specified date range")

        # 2. Load Strategy
        # [FIX] Unmask errors: Remove broad try-except and allow errors to bubble up
        loader = StrategyLoader()
        strategy_class = loader.load_strategy(args.strategy_name)

        if strategy_class is None:
             # Fallback to checking presets directly if loader didn't find it (or if loader only does user files)
            if args.strategy_name in PRESET_STRATEGIES:
                 strategy_class = PRESET_STRATEGIES[args.strategy_name]
            else:
                # Should not happen if load_strategy raises error, but kept for safety
                raise ValueError(f"Strategy not found: {args.strategy_name}")

        # 3. Initialize Engine
        engine = BacktestEngine(initial_capital=10000.0)
        
        # Instantiate strategy with params
        # Check if strategy accepts params
        try:
            strategy = strategy_class(**strategy_params)
        except TypeError:
            # Fallback for strategies that don't accept kwargs or have different init
            # print("Warning: Strategy does not accept params in __init__, ignoring.", file=sys.stderr)
            strategy = strategy_class()
        
        # Generate Signals
        # [FIX] BacktestEngine expects signals Series, not strategy object
        signals_df = strategy.generate_signals(df)
        if 'signal' not in signals_df.columns:
             raise ValueError("Strategy output must contain 'signal' column")
        signals = signals_df['signal']
        
        # 4. Run Backtest
        engine.run(df, signals)
        
        # 5. Calculate Performance
        from src.analytics.performance import calculate_metrics
        
        equity_curve = pd.DataFrame(engine.equity_curve)
        
        if equity_curve.empty:
            print("No trades executed or data empty.")
            performance = calculate_metrics(pd.DataFrame(), [], 10000.0)
        else:
            equity_curve['date'] = pd.to_datetime(equity_curve['date'])
            equity_curve = equity_curve.set_index('date')
            
            performance = calculate_metrics(equity_curve, engine.trades, engine.initial_capital)
        
        # 6. Output Results
        if args.json:
            # Convert performance dict to JSON
            # Handle non-serializable types if any (like numpy types)
            def default_converter(o):
                if isinstance(o, (pd.Timestamp, datetime)):
                    return o.isoformat()
                if isinstance(o, (np.int64, np.int32)):
                    return int(o)
                if isinstance(o, (np.float64, np.float32)):
                    return float(o)
                return str(o)
                
            print(json.dumps(performance, default=default_converter, indent=2))
        else:
            print("Backtest Results:")
            print("-" * 30)
            for k, v in performance.items():
                if isinstance(v, float):
                    print(f"{k}: {v:.4f}")
                else:
                    print(f"{k}: {v}")
            print("-" * 30)
            
    except KeyError as e:
        print(f"CRITICAL ERROR: Missing column {e}.", file=sys.stderr)
        # Try to access engine.data if available, or just print generic help
        # Since 'df' is local variable in try block, we might not have access if error happened before df creation.
        # But if it happened during strategy execution, df exists.
        # We can't easily access local 'df' from here unless we define it outside.
        # However, we can catch it inside the try block or just print a general message.
        # Better: Let's assume if it's a KeyError during backtest, it's likely a column issue.
        print("DEBUG: This usually means the strategy is trying to access a column that doesn't exist.", file=sys.stderr)
        print("DEBUG: Ensure your strategy uses lowercase column names (e.g., 'close', 'open').", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error executing backtest: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
