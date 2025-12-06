from datetime import datetime
from typing import List, Optional
import queue
from src.core.events import Event, OrderEvent, FillEvent

class ExecutionHandler:
    """
    Simulates execution handling (filling orders).
    In a real system, this would connect to a Broker API (IB, Binance).
    Here, it acts as a simulator that fills 'MKT' orders immediately at current prices.
    """
    def __init__(self, events_queue: queue.Queue):
        self.events = events_queue

    def execute_order(self, event: OrderEvent, current_prices: dict, timestamp: datetime, 
                      slippage: float = 0.0, commission_model: Optional[object] = None):
        """
        Converts OrderEvent to FillEvent based on current market data.
        """
        if event.type != getattr(event, 'type', 'ORDER'): # Enum check is safer but string for now
             # In strict typing we'd use EventType.ORDER
             pass

        symbol = event.symbol
        if symbol not in current_prices:
            print(f"Execution Error: No price for {symbol}")
            return

        price = current_prices[symbol]
        
        # Apply Slippage
        # Buy: Pay more (Price * (1+slippage))
        # Sell: Receive less (Price * (1-slippage))
        if event.direction == 'BUY':
            fill_price = price * (1.0 + slippage)
        else:
            fill_price = price * (1.0 - slippage)

        fill_cost = fill_price * event.quantity
        
        # Calculate Commission
        commission = 0.0
        if commission_model:
            commission = commission_model.calculate(fill_cost, event.quantity)
        
        fill_event = FillEvent(
            timestamp=timestamp,
            symbol=symbol,
            exchange="SIM_EXCHANGE",
            quantity=event.quantity,
            direction=event.direction,
            fill_cost=fill_cost,
            commission=commission
        )
        
        self.events.put(fill_event)
