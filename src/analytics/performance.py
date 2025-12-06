import pandas as pd
import numpy as np

from src.config.settings import settings

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

def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = settings.RISK_FREE_RATE) -> float:
    """
    Calculate Sharpe Ratio.
    (Daily_Returns.mean() - Risk_Free_Rate_Daily) / Daily_Returns.std() * sqrt(252)
    """
    if returns.empty:
        return 0.0
        
    std = returns.std()
    if np.isnan(std) or std < 1e-9:
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

def calculate_metrics(equity_curve: pd.DataFrame, trades: list, initial_capital: float) -> dict:
    """
    Calculate standard performance metrics.
    
    Args:
        equity_curve: DataFrame with 'equity', 'position_value' columns and datetime index.
        trades: List of Trade objects.
        initial_capital: Starting capital.
        
    Returns:
        Dictionary of metrics.
    """
    if equity_curve.empty:
        return {
            "total_return": 0.0,
            "cagr": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "win_rate": 0.0,
            "trades": 0,
            "avg_exposure": 0.0
        }
        
    start_equity = initial_capital
    end_equity = equity_curve['equity'].iloc[-1]
    
    # CAGR
    years = (equity_curve.index[-1] - equity_curve.index[0]).days / 365.25
    cagr = calculate_cagr(start_equity, end_equity, years)
    
    # Max Drawdown
    max_dd = calculate_max_drawdown(equity_curve['equity'])
    
    # Sharpe
    daily_returns = equity_curve['equity'].pct_change().fillna(0)
    sharpe = calculate_sharpe_ratio(daily_returns)
    
    # Win Rate
    # Use simple win rate based on trade count for now, or use round_trip if available
    # The UI uses round_trip for win rate, let's stick to simple trade PnL if possible or reuse calculate_win_rate
    # But calculate_win_rate takes a Series of PnL.
    # Let's use calculate_round_trip_returns to be consistent with UI.
    trade_returns = calculate_round_trip_returns(trades)
    win_rate = len([r for r in trade_returns if r > 0]) / len(trade_returns) if trade_returns else 0.0
    
    # Avg Exposure
    # Exposure = Abs(Position Value) / Equity
    if 'position_value' in equity_curve.columns:
        exposure_series = equity_curve['position_value'].abs() / equity_curve['equity']
        avg_exposure = exposure_series.mean()
    else:
        avg_exposure = 0.0
        
    return {
        "total_return": (end_equity / start_equity) - 1,
        "cagr": cagr,
        "max_drawdown": max_dd,
        "sharpe_ratio": sharpe,
        "win_rate": win_rate,
        "trades": len(trades),
        "avg_exposure": avg_exposure
    }
