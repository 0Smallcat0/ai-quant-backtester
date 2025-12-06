import pandas as pd
import queue
import math
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.config.settings import settings
from src.core.events import EventType, MarketEvent, SignalEvent, OrderEvent, FillEvent
from src.execution.execution_handler import ExecutionHandler

@dataclass
class Trade:
    entry_date: pd.Timestamp
    entry_price: float
    quantity: float
    type: str
    entry_equity: float = 0.0
    commission: float = 0.0

class BacktestEngine:
    """
    Event-driven Backtest Engine (v2.0).
    
    Uses a Queue-based event loop to process Market, Signal, Order, and Fill events.
    """
    def __init__(self, initial_capital: float = settings.INITIAL_CAPITAL, 
                 commission_rate: float = settings.COMMISSION_RATE, 
                 slippage: float = settings.SLIPPAGE, 
                 min_commission: float = settings.MIN_COMMISSION, 
                 long_only: bool = False):
        
        self.initial_capital = float(initial_capital)
        self.current_capital = float(initial_capital)
        self.commission_rate = float(commission_rate)
        self.slippage = float(slippage)
        self.min_commission = float(min_commission)
        self.long_only = long_only
        
        # Event Architecture
        self.events = queue.Queue()
        self.execution_handler = ExecutionHandler(self.events)
        
        # State
        self.trades: List[Trade] = []
        self._equity_list: List[Dict[str, Any]] = []
        self.equity_curve: pd.DataFrame = pd.DataFrame()
        self.position = 0.0
        self.latest_prices: Dict[str, float] = {}
        
        # Position Sizing Settings
        self.position_sizing_method = "fixed_percent"
        self.position_sizing_target = 0.95

    def set_position_sizing(self, method: str, target: Optional[float] = None, amount: Optional[float] = None) -> None:
        self.position_sizing_method = method
        if method == "fixed_percent" and target is not None:
            self.position_sizing_target = float(target)
        elif method == "fixed_amount" and amount is not None:
            self.position_sizing_target = float(amount)

    def _get_current_equity(self, price: float) -> float:
        return self.current_capital + (self.position * price)

    def _process_event(self, event) -> None:
        """
        Main Event Dispatcher.
        """
        if event.type == EventType.MARKET:
            # Market Update - Update internal state if needed (usually handled by strategy looking at data)
            pass

        elif event.type == EventType.SIGNAL:
            self._handle_signal(event)

        elif event.type == EventType.ORDER:
            # Route to Execution Handler
            # In a real engine, we might check risk limits here first
            self.execution_handler.execute_order(
                event, 
                self.latest_prices, 
                event.timestamp, # Use event timestamp? Or market time?
                self.slippage,
                self # Passing self as commission model provider logic
            )

        elif event.type == EventType.FILL:
            self._handle_fill(event)

    def calculate(self, fill_cost: float, quantity: float) -> float:
        """Commission Calculation Interface for ExecutionHandler."""
        trade_value = fill_cost
        return max(trade_value * self.commission_rate, self.min_commission)

    def _handle_signal(self, event: SignalEvent) -> None:
        """
        Converts Signal to Order based on Position Sizing.
        Target-Delta execution logic.
        """
        timestamp = event.timestamp
        symbol = event.symbol
        signal_strength = event.strength # Target exposure (-1.0 to 1.0)
        
        # [V2.0 CORE] Check for HRP Fused Weights
        # If the signal event carries a portfolio allocation (HRP), override the simple strength
        if hasattr(event, 'fused_weights') and event.fused_weights:
            # For single-ticker engine, we look up our symbol
            weight = event.fused_weights.get(symbol)
            if weight is not None:
                signal_strength = float(weight)
        
        # Ghost Trade Filtering
        if abs(signal_strength) < 0.01:
            signal_strength = 0.0

        current_price = self.latest_prices.get(symbol)
        if not current_price:
            return

        current_equity = self._get_current_equity(current_price)

        # 1. Calculate Target Quantity
        target_qty = 0.0
        
        if self.position_sizing_method == "fixed_amount":
            target_exposure = self.position_sizing_target * signal_strength
            target_qty = target_exposure / (current_price + settings.EPSILON)
        else: # fixed_percent
            target_exposure = current_equity * self.position_sizing_target * signal_strength
            target_qty = target_exposure / (current_price + settings.EPSILON)

        # Minimum Exposure Filter
        target_value = target_qty * current_price
        if abs(target_value) < (current_equity * settings.MIN_EXPOSURE_THRESHOLD):
            target_qty = 0.0

        # Long Only Enforce
        if self.long_only:
            target_qty = max(0.0, target_qty)

        # 2. Calculate Delta
        delta_qty = target_qty - self.position
        
        # 3. Generate Order
        if abs(delta_qty) > settings.EPSILON:
            direction = "BUY" if delta_qty > 0 else "SELL"
            quantity = abs(delta_qty)
            
            # Simple Cash Check for BUY (Approximate, exact check is at Fill/Exec)
            if direction == "BUY":
                est_cost = quantity * current_price
                if est_cost > self.current_capital:
                    # Cap quantity
                    quantity = math.floor(self.current_capital / (current_price * (1+self.commission_rate)))
            
            # Oversell Protection
            if direction == "SELL" and self.long_only:
                 quantity = min(quantity, self.position)

            if quantity > settings.EPSILON:
                order = OrderEvent(symbol, "MKT", quantity, direction)
                # Hack: Attach timestamp to order for logging/exec
                order.timestamp = timestamp 
                self.events.put(order)

    def _handle_fill(self, event: FillEvent) -> None:
        """
        Updates Portfolio State from Fill.
        """
        if event.direction == "BUY":
            total_cost = event.net_cost() # Cost + Comm
            self.current_capital -= total_cost
            self.position += event.quantity
        else: # SELL
            net_proceeds = event.net_cost() # Cost - Comm (FillCost is positive, net_cost handles logic?)
            # Wait, net_cost implementation:
            # BUY: cost + comm
            # SELL: cost - comm
            # Correct.
            self.current_capital += net_proceeds
            self.position -= event.quantity
            
            if abs(self.position) < settings.EPSILON:
                self.position = 0.0

        self.trades.append(Trade(
            entry_date=event.timestamp,
            entry_price=event.fill_cost / event.quantity, # Avg Price
            quantity=event.quantity,
            type=event.direction,
            entry_equity=self._get_current_equity(self.latest_prices.get(event.symbol, 0)),
            commission=event.commission
        ))

    def run(self, data: pd.DataFrame, signals: pd.Series, start_date: Optional[str] = None, end_date: Optional[str] = None) -> None:
        """
        Executes the backtest using the Event Loop.
        Adapts vectorized inputs (data/signals) into a stream of events.
        """
        # Reset State
        self.current_capital = self.initial_capital
        self.position = 0.0
        self.trades = []
        self._equity_list = []
        self.equity_curve = pd.DataFrame()
        self.latest_prices = {}
        
        # Pre-process Data
        df = data.copy()
        df.columns = [c.lower() for c in df.columns]
        
        if start_date:
            df = df[df.index >= pd.Timestamp(start_date)]
        if end_date:
            df = df[df.index <= pd.Timestamp(end_date)]
            
        if df.empty:
            print("No data for backtest.")
            return

        # Align Signals (Shift logic preserved for safety)
        if isinstance(signals, pd.DataFrame):
             aligned_signals = signals['signal'].shift(1).fillna(0)
             if 'target_size' in signals.columns:
                 # TODO: Support advanced target size passed in signal event
                 pass
        else:
             aligned_signals = signals.shift(1).fillna(0)
             
        # Combine
        combined = df.join(aligned_signals.rename("signal"), how="left").fillna({"signal": 0})
        
        # -------------------------------------------------------------
        # THE EVENT LOOP (Vectorized Hybrid)
        # -------------------------------------------------------------
        # Optimization: Convert to Numpy for fast iteration (avoid iterrows)
        dates = combined.index.to_numpy()
        opens = combined['open'].to_numpy()
        closes = combined['close'].to_numpy()
        signals_arr = combined['signal'].to_numpy()
        
        n_rows = len(dates)
        
        for i in range(n_rows):
            date = dates[i]
            current_price = opens[i] # Trade at Open
            close_price = closes[i]
            signal_val = signals_arr[i]
            
            self.latest_prices['TICKER'] = current_price 
            
            # [PERFORMANCE] Optimization: Remove redundant MarketEvent (No-op in V2)
            # self.events.put(MarketEvent(date))
            
            # [PERFORMANCE] Optimization: Only fire SignalEvent if state change is possible
            # If Signal is 0 and we have no position, nothing happens.
            if signal_val != 0 or abs(self.position) > settings.EPSILON:
                 self.events.put(SignalEvent("Strat1", 'TICKER', date, "TARGET", strength=signal_val))
            
            # 4. Process Events
            while not self.events.empty():
                event = self.events.get()
                self._process_event(event)
                
            # 5. End of Day Accounting
            self.latest_prices['TICKER'] = close_price
            current_equity = self._get_current_equity(close_price)
            position_value = self.position * close_price
            
            self._equity_list.append({
                "date": date,
                "equity": current_equity,
                "cash": self.current_capital,
                "position_value": position_value
            })
            
            if current_equity <= 0:
                print(f"Bankruptcy at {date}")
                break

        self.equity_curve = pd.DataFrame(self._equity_list)