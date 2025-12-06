import pandas as pd
import numpy as np

def generate_dashboard_data(performance: dict, df: pd.DataFrame, ticker: str, equity_curve: pd.DataFrame) -> dict:
    """
    Generate the dashboard data structure required for the UI.
    
    Args:
        performance (dict): Performance metrics dictionary.
        df (pd.DataFrame): The data used for backtesting (contains sentiment if available).
        ticker (str): The ticker symbol.
        equity_curve (pd.DataFrame): The equity curve dataframe.
        
    Returns:
        dict: The complete dashboard data dictionary.
    """
    # A. Health
    # Simple simulation: 0.8 * sharpe
    sharpe = performance.get('sharpe_ratio', 0.0)
    if sharpe is None: sharpe = 0.0
    proj_sharpe = 0.8 * sharpe
    
    if proj_sharpe > 1.5:
        health_status = "Excellent"
        health_color = "green"
    elif proj_sharpe > 1.0:
        health_status = "Good"
        health_color = "blue"
    elif proj_sharpe > 0.5:
        health_status = "Fair"
        health_color = "yellow"
    else:
        health_status = "Poor"
        health_color = "red"
        
    health = {
        "status": health_status,
        "color": health_color,
        "projected_sharpe": round(proj_sharpe, 2),
        "original_sharpe": round(sharpe, 2)
    }
    
    # B. Market Weather
    # Get latest sentiment
    weather_status = "Neutral" # Default
    weather_score = 0.0
    
    if 'sentiment' in df.columns and not df.empty:
            # Get last value (iloc -1 could be NaN)
            last_val = df['sentiment'].ffill().iloc[-1]
            if pd.isna(last_val):
                last_val = 0.0
            weather_score = float(last_val)
            
            if weather_score > 0.5: weather_status = "Sunny"
            elif weather_score > 0.1: weather_status = "Clear"
            elif weather_score < -0.5: weather_status = "Stormy"
            elif weather_score < -0.1: weather_status = "Rainy"
            else: weather_status = "Cloudy"
    
    market_weather = {
        "condition": weather_status,
        "score": round(weather_score, 2),
        "insight": f"Market Condition is {weather_status} (Score: {weather_score:.2f}). AI suggests monitoring volatility."
    }
    
    # C. Allocation
    # Since CLI run_backtest runs 1 ticker, allocation is 100% that ticker
    allocation = {
        ticker: 1.0
    }
    
    # D. Merge
    dashboard_data = {
        "version": "2.0",
        "performance": performance,
        "health": health,
        "market_weather": market_weather,
        "allocation": allocation,
        "equity_curve": equity_curve.reset_index().to_dict(orient='records') if not equity_curve.empty else []
    }
    
    return dashboard_data
