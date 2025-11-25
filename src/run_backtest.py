import argparse
import sys
import json
import pandas as pd
from datetime import datetime
import os
import logging

# Add src to python path to allow imports
try:
    from src.utils import add_project_root, sanitize_ticker
except ImportError:
    from utils import add_project_root, sanitize_ticker
add_project_root()

from src.data_engine import DataManager
from src.strategies.loader import StrategyLoader
from src.backtest_engine import BacktestEngine
from src.strategies.presets import PRESET_STRATEGIES
from src.config.settings import settings

def main():
    parser = argparse.ArgumentParser(description="Run a backtest for a specific strategy.")
    parser.add_argument("--strategy_name", required=True, help="Name of the strategy class")
    parser.add_argument("--ticker", "--symbol", dest="ticker", default="BTC-USD", help="Ticker symbol (e.g., AAPL)")
    parser.add_argument("--start", "--start_date", "--from", dest="start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", "--end_date", "--to", dest="end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--params", help="JSON string of strategy params")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    
    args = parser.parse_args()
    
    # Configure Logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # [FIX] Sanitize arguments by stripping quotes
    if args.ticker:
        args.ticker = sanitize_ticker(args.ticker)
    if args.strategy_name:
        args.strategy_name = args.strategy_name.strip().strip("'").strip('"')
    if args.start:
        # [FIX] Do not use sanitize_ticker for dates as it upper-cases them
        args.start = args.start.strip().strip("'").strip('"')
    if args.end:
        args.end = args.end.strip().strip("'").strip('"')
    
    # Parse params
    strategy_params = {}
    if args.params:
        try:
            # Handle potential double quotes issues from shell
            cleaned_params = args.params.strip("'").strip('"')
            strategy_params = json.loads(cleaned_params)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing params JSON: {e}")
            sys.exit(1)
    
    # [FIX] Ensure root dir AND src dir are in sys.path
    # Handled by add_project_root()

    # try: # [REFACTOR] Removed broad try-except to allow traceback for unknown errors
    # 1. Load Data
    logger.info(f"Loading data for {args.ticker}...")
    data_manager = DataManager(db_path=str(settings.DB_PATH))
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
        # logger.warning("Strategy does not accept params in __init__, ignoring.")
        strategy = strategy_class()
        
    # Generate Signals
    # [FIX] BacktestEngine expects signals Series, not strategy object
    signals_df = strategy.generate_signals(df)
    if 'signal' not in signals_df.columns:
            raise ValueError("Strategy output must contain 'signal' column")
    signals = signals_df['signal']
    
    # 4. Run Backtest
    logger.info("Running backtest...")
    engine.run(df, signals)
    
    # 5. Calculate Performance
    from src.analytics.performance import calculate_metrics
    
    equity_curve = engine.equity_curve
    
    # Convert to DataFrame if list
    if isinstance(equity_curve, list):
        equity_curve = pd.DataFrame(equity_curve)

    if equity_curve.empty:
        logger.warning("No trades executed or data empty.")
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
        logger.info("Backtest Results:")
        print("-" * 30)
        for k, v in performance.items():
            if isinstance(v, float):
                print(f"{k}: {v:.4f}")
            else:
                print(f"{k}: {v}")
        print("-" * 30)
            
    # except KeyError as e:
    #     logger.error(f"CRITICAL ERROR: Missing column {e}.")
    #     logger.debug("This usually means the strategy is trying to access a column that doesn't exist.")
    #     logger.debug("Ensure your strategy uses lowercase column names (e.g., 'close', 'open').")
    #     sys.exit(1)
    # except Exception as e:
    #     logger.error(f"Error executing backtest: {e}")
    #     sys.exit(1)

if __name__ == "__main__":
    main()
