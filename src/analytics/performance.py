import pandas as pd
import numpy as np

def calculate_cagr(start_value: float, end_value: float, years: float) -> float:
    """
    Calculate CAGR (Compound Annual Growth Rate).
    (End_Value / Start_Value) ^ (1 / Years) - 1
    """
    if start_value <= 0:
        return 0.0
    if end_value <= 0:
        return -1.0
    if years < 0.001:
        return 0.0
        
    try:
        return (end_value / start_value) ** (1 / years) - 1
    except (ZeroDivisionError, ValueError):
        return 0.0

def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """
    Calculate Max Drawdown.
    """
    if equity_curve.empty:
        return 0.0
    
    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax
    return drawdown.min()

def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """
    Calculate Sharpe Ratio.
    (Daily_Returns.mean() - Risk_Free_Rate_Daily) / Daily_Returns.std() * sqrt(252)
    """
    if returns.empty or returns.std() == 0:
        return 0.0
    
    # Convert annual risk free rate to daily
    # Or assume risk_free_rate input is annual and we adjust in formula
    # The formula in requirements: (Daily_Returns.mean() - Risk_Free_Rate) / Daily_Returns.std() * sqrt(252)
    # Usually Risk_Free_Rate in formula is daily if subtracting from daily returns.
    # If input is 0.02 (annual), daily is approx 0.02/252.
    
    rf_daily = risk_free_rate / 252
    excess_returns = returns - rf_daily
    return np.sqrt(252) * (excess_returns.mean() / returns.std())

def calculate_win_rate(trades_pnl: pd.Series) -> float:
    """
    Calculate Win Rate.
    """
    if trades_pnl.empty:
        return 0.0
    
    # Filter out flat trades? Requirement says: "獲利交易次數 / 總交易次數"
    # Usually we count total trades.
    total_trades = len(trades_pnl)
    if total_trades == 0:
        return 0.0
        
    winning_trades = (trades_pnl > 0).sum()
    return winning_trades / total_trades

def calculate_round_trip_returns(trades: list, commission_rate: float = 0.0) -> list:
    """
    Calculate round-trip trade returns using FIFO matching.
    
    Args:
        trades: List of Trade objects from BacktestEngine.
        commission_rate: Commission rate per trade (e.g., 0.001 for 0.1%).
        
    Returns:
        List of float returns (percentage, e.g., 0.05 for 5%).
    """
    import collections
    
    buy_queue = collections.deque()   # Waiting for SELL (Longs)
    sell_queue = collections.deque()  # Waiting for BUY (Shorts)
    returns = []
    
    for t in trades:
        if t.type == 'BUY':
            qty_to_buy = t.quantity
            
            # 1. Check if we need to cover any Short positions (Short Cover)
            while qty_to_buy > 0 and sell_queue:
                matched_short = sell_queue[0]
                matched_qty = min(qty_to_buy, matched_short['qty'])
                
                # Calculate Short Return
                # Profit = (Short_Entry_Price - Buy_Cover_Price) * Qty
                if matched_short['entry_equity'] > 0:
                    gross_pnl = (matched_short['price'] - t.entry_price) * matched_qty
                    
                    total_commission = (matched_short['price'] * matched_qty * commission_rate) + \
                                       (t.entry_price * matched_qty * commission_rate)
                                       
                    net_pnl = gross_pnl - total_commission
                    ret = net_pnl / matched_short['entry_equity']
                    returns.append(ret)
                else:
                    # Legacy fallback
                    if matched_short['price'] > 0:
                        ret = (matched_short['price'] - t.entry_price) / matched_short['price']
                        returns.append(ret)
                
                # Update state
                qty_to_buy -= matched_qty
                matched_short['qty'] -= matched_qty
                
                if matched_short['qty'] <= 0:
                    sell_queue.popleft()
            
            # 2. If quantity remains, it's a new Long Entry
            if qty_to_buy > 0:
                buy_queue.append({
                    'price': t.entry_price,
                    'qty': qty_to_buy,
                    'entry_equity': getattr(t, 'entry_equity', 0.0)
                })

        elif t.type == 'SELL':
            qty_to_sell = t.quantity
            
            # 1. Check if we need to close any Long positions (Long Exit)
            while qty_to_sell > 0 and buy_queue:
                matched_buy = buy_queue[0]
                matched_qty = min(qty_to_sell, matched_buy['qty'])
                
                # Calculate Long Return
                # Profit = (Sell_Price - Buy_Entry_Price) * Qty
                if matched_buy['entry_equity'] > 0:
                    gross_pnl = (t.entry_price - matched_buy['price']) * matched_qty
                    
                    total_commission = (matched_buy['price'] * matched_qty * commission_rate) + \
                                       (t.entry_price * matched_qty * commission_rate)
                                       
                    net_pnl = gross_pnl - total_commission
                    ret = net_pnl / matched_buy['entry_equity']
                    returns.append(ret)
                else:
                    # Legacy fallback
                    if matched_buy['price'] > 0:
                        ret = (t.entry_price - matched_buy['price']) / matched_buy['price']
                        returns.append(ret)
                
                # Update state
                qty_to_sell -= matched_qty
                matched_buy['qty'] -= matched_qty
                
                if matched_buy['qty'] <= 0:
                    buy_queue.popleft()
            
            # 2. If quantity remains, it's a new Short Entry
            if qty_to_sell > 0:
                sell_queue.append({
                    'price': t.entry_price,
                    'qty': qty_to_sell,
                    'entry_equity': getattr(t, 'entry_equity', 0.0)
                })
                    
    return returns
