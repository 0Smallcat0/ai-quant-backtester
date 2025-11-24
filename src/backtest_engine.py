import pandas as pd
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import math
import numpy as np
from config.settings import (
    DEFAULT_INITIAL_CAPITAL, DEFAULT_COMMISSION_RATE, DEFAULT_SLIPPAGE_RATE, 
    DEFAULT_MIN_COMMISSION, EPSILON
)

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
    def __init__(self, initial_capital: float = DEFAULT_INITIAL_CAPITAL, commission_rate: float = DEFAULT_COMMISSION_RATE, slippage_rate: float = DEFAULT_SLIPPAGE_RATE, min_commission: float = DEFAULT_MIN_COMMISSION, long_only: bool = False):
        """
        Initializes the BacktestEngine.

        Args:
            initial_capital (float): Starting capital for the portfolio.
            commission_rate (float): Commission rate per trade (e.g., 0.001 for 0.1%).
            slippage_rate (float): Simulated slippage rate (e.g., 0.001 for 0.1%).
            min_commission (float): Minimum commission per trade in dollars.
            long_only (bool): If True, short selling is disabled.
        """
        self.initial_capital = float(initial_capital)
        self.current_capital = float(initial_capital)
        self.commission_rate = float(commission_rate)
        self.slippage_rate = float(slippage_rate)
        self.min_commission = float(min_commission)
        self.long_only = long_only
        
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict[str, Any]] = []
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

    def run(self, data: pd.DataFrame, signals: pd.Series) -> None:
        """
        Executes the backtest loop using Target-Delta execution logic.

        Args:
            data (pd.DataFrame): OHLCV data with a DateTimeIndex.
            signals (pd.Series): Series of trading signals.
                                 Magnitude indicates target exposure (e.g., 1.0 = 100% Long, -0.5 = 50% Short).
                                 0.0 = Flat/Cash.
        """
        self.current_capital = self.initial_capital
        self.position = 0.0
        self.trades = []
        self.equity_curve = []
        self.pending_order = None
        
        # [ROBUSTNESS] 1. Input Data Validation & Normalization
        # Create a copy to avoid modifying the original dataframe
        df = data.copy()
        df.columns = [c.lower() for c in df.columns]
        
        required_cols = ['open', 'close']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Input data must contain columns: {required_cols}. Missing: {missing}")
            
        # Align data and signals
        combined = df.join(signals.rename("signal"), how="left").fillna({"signal": 0})
        
        # [SAFETY] Pre-flight Data Integrity Check
        if combined.isnull().values.any():
            raise ValueError("Input data contains NaN values. Please clean data before backtesting.")
        if np.isinf(combined.select_dtypes(include=np.number)).values.any():
            raise ValueError("Input data contains Infinite values. Please clean data before backtesting.")

        for date, row in combined.iterrows():
            # ---------------------------------------------------
            # 1. Market Open: Execute Pending Orders (T+1)
            # ---------------------------------------------------
            if self.pending_order:
                raw_price = float(row["open"])
                
                # Apply Slippage
                if self.pending_order.type == "BUY":
                    execution_price = raw_price * (1 + self.slippage_rate)
                else: # SELL
                    execution_price = raw_price * (1 - self.slippage_rate)
                
                quantity = self.pending_order.quantity
                
                if quantity > EPSILON:
                    trade_value = quantity * execution_price
                    commission = max(trade_value * self.commission_rate, self.min_commission)
                    
                    if self.pending_order.type == "BUY":
                        # Bankruptcy Protection: Cap quantity at available capital
                        # Calculate max quantity considering both proportional and minimum commission
                        denom_rate = execution_price * (1 + self.commission_rate)
                        max_qty_rate = self.current_capital / (denom_rate + EPSILON)
                        
                        max_qty_fixed = (self.current_capital - self.min_commission) / (execution_price + EPSILON)
                        
                        # Use the most conservative limit
                        max_buyable = max(0.0, min(max_qty_rate, max_qty_fixed))
                        quantity = min(quantity, max_buyable)
                        
                        trade_value = quantity * execution_price
                        commission = max(trade_value * self.commission_rate, self.min_commission)
                        total_cost = trade_value + commission

                        if self.current_capital >= total_cost - EPSILON and quantity > EPSILON:
                            self.current_capital -= total_cost
                            self.position += quantity
                            self.trades.append(Trade(
                                entry_date=date,
                                entry_price=execution_price,
                                quantity=abs(quantity),
                                type="BUY",
                                entry_equity=self._get_current_equity(execution_price)
                            ))
                    
                    elif self.pending_order.type == "SELL":
                        # [ROBUSTNESS] Oversell Protection
                        # Ensure we don't sell more than we have due to float errors
                        # ONLY apply this if we are in Long-Only mode. 
                        # If Shorting is allowed, we can sell more than we have (going negative).
                        if self.long_only:
                            quantity = min(quantity, self.position)
                        
                        if quantity > EPSILON:
                            trade_value = quantity * execution_price
                            commission = max(trade_value * self.commission_rate, self.min_commission)
                            net_revenue = trade_value - commission
                            
                            self.current_capital += net_revenue
                            self.position -= quantity
                            
                            # [ROBUSTNESS] Fix floating point drift if position is near zero
                            if abs(self.position) < EPSILON:
                                self.position = 0.0
                                
                            self.trades.append(Trade(
                                entry_date=date,
                                entry_price=execution_price,
                                quantity=abs(quantity),
                                type="SELL",
                                entry_equity=self._get_current_equity(execution_price)
                            ))
                
                self.pending_order = None

            # ---------------------------------------------------
            # 2. Market Close: Process Signals & Calculate Target
            # ---------------------------------------------------
            # Current Equity (at Close) used for sizing
            current_close = float(row["close"])
            current_equity = self._get_current_equity(current_close)
            
            # Bankruptcy Check (Early Exit)
            if current_equity <= 0:
                # [ROBUSTNESS] Bankruptcy Curve Filling
                # Fill the current date
                self.equity_curve.append({
                    "date": date, "equity": 0.0, "cash": 0.0, "position_value": 0.0
                })
                
                # Fill remaining dates
                remaining_dates = combined.index[combined.index > date]
                for d in remaining_dates:
                    self.equity_curve.append({
                        "date": d, "equity": 0.0, "cash": 0.0, "position_value": 0.0
                    })
                
                print(f"Bankruptcy detected at {date}. Stopping backtest.")
                break

            signal = row["signal"]
            
            # Calculate Target Position (Units)
            target_qty = 0.0
            
            # [SAFETY] Division by zero protection
            if current_close > 0:
                if self.position_sizing_method == "fixed_amount":
                    # Signal magnitude scales the fixed amount
                    # e.g. Signal 0.5 * Amount 1000 = Target 500
                    target_exposure = float(self.position_sizing_target) * signal
                    target_qty = target_exposure / (current_close + EPSILON)
                else: # fixed_percent
                    # Signal magnitude scales the equity %
                    # e.g. Signal 0.5 * Target 1.0 (100%) = Target 50% Equity
                    target_exposure = current_equity * float(self.position_sizing_target) * signal
                    target_qty = target_exposure / (current_close + EPSILON)
            
            # Enforce Long-Only
            if self.long_only and target_qty < 0:
                # Suppress SHORT signal in Long-Only mode
                target_qty = 0.0
            elif self.long_only:
                 # Ensure non-negative if not caught above (e.g. -0.0)
                 target_qty = max(0.0, target_qty)
                
            # Calculate Delta
            delta_qty = target_qty - self.position
            
            # Generate Pending Order for Next Open
            # We only trade if delta is significant (optional, but good for noise)
            # For now, trade any non-zero delta
            
            if abs(delta_qty) > EPSILON:
                order_type = "BUY" if delta_qty > 0 else "SELL"
                self.pending_order = Order(
                    date=date, 
                    type=order_type, 
                    quantity=abs(delta_qty)
                )

            # ---------------------------------------------------
            # 3. Update Daily Equity
            # ---------------------------------------------------
            position_value = self.position * current_close
            equity = self.current_capital + position_value
            
            self.equity_curve.append({
                "date": date, 
                "equity": equity,
                "cash": self.current_capital,
                "position_value": position_value
            })