import pandas as pd
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import math
import numpy as np
from src.config.settings import settings

@dataclass
class Order:
    date: pd.Timestamp
    type: str  # 'BUY' or 'SELL'
    quantity: float = 0.0
    
@dataclass
class Trade:
    entry_date: pd.Timestamp
    entry_price: float
    quantity: float
    type: str
    entry_equity: float = 0.0

class BacktestEngine:
    """
    Event-driven Backtest Engine.
    
    Simulates the execution of a trading strategy on historical data, accounting for
    transaction costs (commission, slippage) and position sizing rules.
    """
    def __init__(self, initial_capital: float = settings.INITIAL_CAPITAL, commission_rate: float = settings.COMMISSION_RATE, slippage: float = settings.SLIPPAGE, min_commission: float = settings.MIN_COMMISSION, long_only: bool = False):
        """
        Initializes the BacktestEngine.

        Args:
            initial_capital (float): Starting capital for the portfolio.
            commission_rate (float): Commission rate per trade (e.g., 0.001 for 0.1%).
            slippage (float): Simulated slippage rate (e.g., 0.001 for 0.1%).
            min_commission (float): Minimum commission per trade in dollars.
            long_only (bool): If True, short selling is disabled.
        """
        self.initial_capital = float(initial_capital)
        self.current_capital = float(initial_capital)
        self.commission_rate = float(commission_rate)
        self.slippage = float(slippage)
        self.min_commission = float(min_commission)
        self.long_only = long_only
        
        self.trades: List[Trade] = []
        self._equity_list: List[Dict[str, Any]] = []
        self.equity_curve: pd.DataFrame = pd.DataFrame()
        self.pending_order: Optional[Order] = None
        self.position = 0.0
        
        # Position Sizing Settings
        self.position_sizing_method = "fixed_percent" # Default
        self.position_sizing_target = 0.95 # Default 95%

    def set_position_sizing(self, method: str, target: Optional[float] = None, amount: Optional[float] = None) -> None:
        """
        Configures the position sizing algorithm.

        Args:
            method (str): 'fixed_percent' or 'fixed_amount'.
            target (float, optional): Target percentage (0.0 to 1.0) for 'fixed_percent'.
            amount (float, optional): Target dollar amount for 'fixed_amount'.
        """
        self.position_sizing_method = method
        if method == "fixed_percent":
            if target is not None:
                self.position_sizing_target = float(target)
        elif method == "fixed_amount":
            if amount is not None:
                self.position_sizing_target = float(amount)

    def _get_current_equity(self, price: float) -> float:
        """Calculates total portfolio equity at the given price."""
        return self.current_capital + (self.position * price)

    def run(self, data: pd.DataFrame, signals: pd.Series, start_date: Optional[str] = None, end_date: Optional[str] = None) -> None:
        """
        Executes the backtest loop using Target-Delta execution logic.

        Args:
            data (pd.DataFrame): OHLCV data with a DateTimeIndex.
            signals (pd.Series): Series of trading signals.
                                 Magnitude indicates target exposure (e.g., 1.0 = 100% Long, -0.5 = 50% Short).
                                 0.0 = Flat/Cash.
            start_date (str, optional): Start date for the backtest (inclusive).
            end_date (str, optional): End date for the backtest (inclusive).
        """
        self.current_capital = self.initial_capital
        self.position = 0.0
        self.trades = []
        self._equity_list = []
        self.equity_curve = pd.DataFrame()
        self.pending_order = None
        
        # [ROBUSTNESS] 1. Input Data Validation & Normalization
        # Create a copy to avoid modifying the original dataframe
        df = data.copy()
        df.columns = [c.lower() for c in df.columns]
        
        # [NEW] Date Slicing for Stress Testing / Audit
        if start_date:
            df = df[df.index >= pd.Timestamp(start_date)]
        if end_date:
            df = df[df.index <= pd.Timestamp(end_date)]
            
        if df.empty:
            print(f"Warning: No data found for range {start_date} to {end_date}. Backtest aborted.")
            return

        required_cols = ['open', 'close']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Input data must contain columns: {required_cols}. Missing: {missing}")
            
        # Align data and signals
        # [ARCHITECTURAL ENFORCEMENT] Force T+1 Lag
        # We shift signals by 1 to ensure that a signal generated at T (Close) 
        # is only available for execution at T+1 (Open).
        # This prevents any possibility of look-ahead bias in the execution loop.
        
        # Check if signals is DataFrame or Series
        target_sizes_arr = None
        
        if isinstance(signals, pd.DataFrame):
            # Expect 'signal' column, optional 'target_size'
            if 'signal' not in signals.columns:
                raise ValueError("Signals DataFrame must contain 'signal' column.")
            
            shifted_signals = signals.shift(1).fillna(0)
            
            # Extract signal series
            aligned_signal_series = shifted_signals['signal']
            
            # Extract target_size if exists
            if 'target_size' in shifted_signals.columns:
                # We need to align it with df
                # Join to ensure index alignment
                # Note: We'll handle extraction after join
                pass
            
            # Join everything to df
            # We rename columns to avoid collision if needed, but 'signal' is standard
            combined = df.join(shifted_signals[['signal']], how="left").fillna({"signal": 0})
            
            if 'target_size' in shifted_signals.columns:
                combined = combined.join(shifted_signals[['target_size']], how="left").fillna({"target_size": 0})
                target_sizes_arr = combined['target_size'].values
            
        else:
            # It's a Series
            aligned_signals = signals.shift(1).fillna(0)
            combined = df.join(aligned_signals.rename("signal"), how="left").fillna({"signal": 0})
        
        # [SAFETY] Pre-flight Data Integrity Check
        if combined.isnull().values.any():
            raise ValueError("Input data contains NaN values. Please clean data before backtesting.")
        if np.isinf(combined.select_dtypes(include=np.number)).values.any():
            raise ValueError("Input data contains Infinite values. Please clean data before backtesting.")

        # [OPTIMIZATION] Pre-fetch arrays to avoid .iloc overhead inside loop
        dates = combined.index.values
        opens = combined['open'].values
        highs = combined['high'].values
        lows = combined['low'].values
        closes = combined['close'].values
        signals_arr = combined['signal'].values
        # target_sizes_arr is already set above if available
        
        # Pre-calculate length
        n_candles = len(dates)
        
        for i in range(n_candles):
            # ---------------------------------------------------
            # 1. Signal Processing & Target Calculation (Based on Shifted Signal)
            # ---------------------------------------------------
            # Since signals are shifted by 1, row['signal'] represents the signal from Yesterday (Close).
            # We use this to determine the Target Position for Today (Open).
            
            date = dates[i]
            signal = signals_arr[i]
            current_close = float(closes[i])
            current_open = float(opens[i])
            
            # Calculate Current Equity (at Open) for sizing
            # Note: We use Open price for sizing because we are trading at Open
            current_equity_open = self._get_current_equity(current_open)
            
            # [FIX] Ghost Trade Filtering
            # Filter out extremely small signals that are likely noise or will be eroded by commissions.
            if abs(signal) < 0.01:
                signal = 0.0
            
            # Calculate Target Position (Units)
            target_qty = 0.0
            
            # [SAFETY] Division by zero protection
            if current_open > 0:
                # Determine sizing factor
                if target_sizes_arr is not None:
                    # Use the provided target size from strategy
                    # This overrides the default position_sizing_target
                    sizing_factor = float(target_sizes_arr[i])
                else:
                    # Use default global setting
                    sizing_factor = float(self.position_sizing_target)

                if self.position_sizing_method == "fixed_amount":
                    target_exposure = sizing_factor * signal
                    target_qty = target_exposure / (current_open + settings.EPSILON)
                else: # fixed_percent
                    target_exposure = current_equity_open * sizing_factor * signal
                    target_qty = target_exposure / (current_open + settings.EPSILON)
            
            # [FIX] Minimum Exposure Filter
            # Prevent ghost positions by ensuring target value is at least 0.1% of equity
            # MIN_EXPOSURE_THRESHOLD is now sourced from settings
            target_value = target_qty * current_open
            if abs(target_value) < (current_equity_open * settings.MIN_EXPOSURE_THRESHOLD):
                target_qty = 0.0
            
            # Enforce Long-Only
            if self.long_only and target_qty < 0:
                target_qty = 0.0
            elif self.long_only:
                target_qty = max(0.0, target_qty)
                
            # Calculate Delta
            delta_qty = target_qty - self.position
            
            # ---------------------------------------------------
            # 2. Execution (Market On Open)
            # ---------------------------------------------------
            if abs(delta_qty) > settings.EPSILON:
                order_type = "BUY" if delta_qty > 0 else "SELL"
                quantity = abs(delta_qty)
                
                # Apply Slippage
                if order_type == "BUY":
                    execution_price = current_open * (1 + self.slippage)
                else: # SELL
                    execution_price = current_open * (1 - self.slippage)
                
                trade_executed = False
                
                if order_type == "BUY":
                    # Bankruptcy/Cash Protection
                    denom_rate = execution_price * (1 + self.commission_rate)
                    if denom_rate > settings.EPSILON:
                        max_qty_by_cash = math.floor(self.current_capital / denom_rate)
                    else:
                        max_qty_by_cash = 0.0
                        
                    quantity = min(quantity, float(max_qty_by_cash))
                    
                    trade_value = quantity * execution_price
                    commission = max(trade_value * self.commission_rate, self.min_commission)
                    total_cost = trade_value + commission
                    
                    if self.current_capital >= total_cost - settings.EPSILON and quantity > settings.EPSILON:
                        self.current_capital -= total_cost
                        self.position += quantity
                        trade_executed = True
                
                elif order_type == "SELL":
                    # Oversell Protection
                    if self.long_only:
                        quantity = min(quantity, self.position)
                    
                    if quantity > settings.EPSILON:
                        trade_value = quantity * execution_price
                        commission = max(trade_value * self.commission_rate, self.min_commission)
                        net_revenue = trade_value - commission
                        
                        self.current_capital += net_revenue
                        self.position -= quantity
                        
                        # Fix floating point drift
                        if abs(self.position) < settings.EPSILON:
                            self.position = 0.0
                        
                        trade_executed = True
                
                if trade_executed:
                    self.trades.append(Trade(
                        entry_date=date,
                        entry_price=execution_price,
                        quantity=abs(quantity),
                        type=order_type,
                        entry_equity=self._get_current_equity(execution_price)
                    ))

            # ---------------------------------------------------
            # 3. Market Close: Update Daily Equity & Check Bankruptcy
            # ---------------------------------------------------
            # Recalculate equity at Close
            current_equity_close = self._get_current_equity(current_close)
            
            # Bankruptcy Check
            if current_equity_close <= 0:
                self._equity_list.append({
                    "date": date, "equity": 0.0, "cash": 0.0, "position_value": 0.0
                })
                # Fill remaining dates with 0
                for j in range(i + 1, n_candles):
                    self._equity_list.append({
                        "date": dates[j], "equity": 0.0, "cash": 0.0, "position_value": 0.0
                    })
                print(f"Bankruptcy detected at {date}. Stopping backtest.")
                break

            # ---------------------------------------------------
            # 3. Update Daily Equity
            # ---------------------------------------------------
            position_value = self.position * current_close
            equity = self.current_capital + position_value
            
            self._equity_list.append({
                "date": date, 
                "equity": equity,
                "cash": self.current_capital,
                "position_value": position_value
            })
            
        # [OPTIMIZATION] Convert list to DataFrame at the end
        self.equity_curve = pd.DataFrame(self._equity_list)