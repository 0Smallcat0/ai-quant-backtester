import plotly.graph_objects as go
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots

def plot_trading_chart(df: pd.DataFrame, trades: list) -> go.Figure:
    """
    Plot OHLC candlestick chart with buy/sell markers.
    """
    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='OHLC',
        increasing_line_color='#B0BEC5', # Light Gray for Up
        decreasing_line_color='#37474F'  # Dark Gray for Down
    ))

    # Extract Buy/Sell points
    buy_dates = []
    buy_prices = []
    sell_dates = []
    sell_prices = []

    for trade in trades:
        # Handle both object and dict for robustness
        try:
            date = trade.entry_date
            price = trade.entry_price
            side = trade.type
        except AttributeError:
            date = trade['entry_date']
            price = trade['entry_price']
            side = trade['type']

        # [FIX] Normalize side to upper case for safety
        side = str(side).upper()

        if side == 'BUY':
            buy_dates.append(date)
            buy_prices.append(price)
        elif side == 'SELL':
            sell_dates.append(date)
            sell_prices.append(price)

    # Add Buy Markers (Triangle Up, Green)
    if buy_dates:
        fig.add_trace(go.Scatter(
            x=buy_dates,
            y=buy_prices,
            mode='markers',
            marker=dict(symbol='triangle-up', size=10, color='green'),
            name='Buy Signal'
        ))

    # Add Sell Markers (Triangle Down, Red)
    if sell_dates:
        fig.add_trace(go.Scatter(
            x=sell_dates,
            y=sell_prices,
            mode='markers',
            marker=dict(symbol='triangle-down', size=10, color='red'),
            name='Sell Signal'
        ))

    # Range Selector
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=5, label="5D", step="day", stepmode="backward"),
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(count=5, label="5Y", step="year", stepmode="backward"),
                dict(step="all", label="All")
            ]),
            font=dict(color="white", size=12),
            bgcolor="#333333",
            activecolor="#FF4B4B",
            bordercolor="#555555",
            borderwidth=1
        )
    )

    fig.update_layout(
        title='Trading Signals',
        yaxis_title='Price',
        xaxis_title='Date',
        template='plotly_dark',
        height=600,
        xaxis_rangeslider_visible=False # Ensure Y axis is not locked
    )
    
    # Force Y-Axis Auto-Scaling
    fig.update_yaxes(autorange=True, fixedrange=False)

    return fig

def plot_equity_curve(strategy_equity: pd.DataFrame, benchmark_equity: pd.DataFrame = None) -> go.Figure:
    """
    Plot Equity Curve vs Benchmark (Long-Only & Short-Only).
    """
    fig = go.Figure()

    # 1. Strategy Trace
    # Handle different input formats for strategy_equity
    if isinstance(strategy_equity, pd.DataFrame):
        if 'equity' in strategy_equity.columns:
            y_strategy = strategy_equity['equity']
        else:
            y_strategy = strategy_equity.iloc[:, 0]
        x_strategy = strategy_equity.index
    else:
        # List of dicts case
        df = pd.DataFrame(strategy_equity)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']) # Ensure datetime
            df.set_index('date', inplace=True)
        if 'equity' in df.columns:
            y_strategy = df['equity']
        else:
            y_strategy = df.iloc[:, 0]
        x_strategy = df.index

    # Get Initial Capital from Strategy
    initial_capital = y_strategy.iloc[0] if not y_strategy.empty else 10000

    fig.add_trace(go.Scatter(
        x=x_strategy,
        y=y_strategy,
        mode='lines',
        name='Strategy',
        line=dict(color='#00CC96', width=2)
    ))

    # 2. Benchmark Traces
    if benchmark_equity is not None:
        # Extract Series from DataFrame if needed
        if isinstance(benchmark_equity, pd.DataFrame):
            if 'equity' in benchmark_equity.columns:
                bench_series = benchmark_equity['equity']
            elif 'close' in benchmark_equity.columns:
                bench_series = benchmark_equity['close']
            else:
                bench_series = benchmark_equity.iloc[:, 0]
        else:
            bench_series = benchmark_equity

        # Ensure we have a Series for calculation
        if not isinstance(bench_series, pd.Series):
            bench_series = pd.Series(bench_series)

        # [FIX] Align Benchmark Date Range to Strategy Range
        # This prevents the benchmark line from extending way beyond the backtest period
        if not bench_series.empty and not y_strategy.empty:
            start_date = x_strategy.min()
            end_date = x_strategy.max()
            # Clip benchmark to strategy period
            bench_series = bench_series.loc[(bench_series.index >= start_date) & (bench_series.index <= end_date)]

        # Normalize Benchmark (Long-Only) to Initial Capital
        if not bench_series.empty:
            bench_start = bench_series.iloc[0]
            if bench_start != 0:
                long_equity = initial_capital * (bench_series / bench_start)
            else:
                long_equity = bench_series 

            # 2. Long-Only Trace (Benchmark)
            fig.add_trace(go.Scatter(
                x=long_equity.index,
                y=long_equity,
                mode='lines',
                name='Long Only (Buy & Hold)',
                line=dict(color='green', dash='dash', width=1)
            ))

            # 3. Short-Only Trace (Calculated)
            # Short Equity = Initial + (Initial - Long_Equity)
            short_equity = initial_capital + (initial_capital - long_equity)
            
            fig.add_trace(go.Scatter(
                x=short_equity.index,
                y=short_equity,
                mode='lines',
                name='Short Only (Short & Hold)',
                line=dict(color='red', dash='dash', width=1)
            ))

    # 4. Layout & Scaling Fix
    fig.update_layout(
        title='Equity Curve Comparison',
        xaxis_title='Date',
        yaxis_title='Equity ($)',
        template='plotly_dark',
        xaxis_rangeslider_visible=False, # Ensure Y axis is not locked
        hovermode='x unified',
        height=500
    )
    fig.update_yaxes(autorange=True, fixedrange=False)

    return fig

def plot_monte_carlo_simulation(sim_results: dict) -> go.Figure:
    """
    Plot Monte Carlo Simulation Cloud and Percentiles.
    """
    fig = go.Figure()
    
    curves = sim_results.get('curves', [])
    p5 = sim_results.get('p5', [])
    p50 = sim_results.get('p50', [])
    p95 = sim_results.get('p95', [])
    
    if len(curves) == 0:
        return fig
        
    x_axis = list(range(len(p5)))
    
    # Plot Cloud (Subset of simulations for performance)
    n_sims = len(curves)
    n_plot = min(n_sims, 100) # Plot at most 100 lines
    # Ensure we don't crash if n_sims < 100 (though unlikely with default settings)
    if n_sims > 0:
        indices = np.random.choice(n_sims, n_plot, replace=False)
        
        for idx in indices:
            fig.add_trace(go.Scatter(
                x=x_axis,
                y=curves[idx],
                mode='lines',
                line=dict(color='gray', width=1),
                opacity=0.1,
                showlegend=False,
                hoverinfo='skip'
            ))
        
    # Plot Percentiles
    fig.add_trace(go.Scatter(
        x=x_axis,
        y=p95,
        mode='lines',
        name='P95 (Optimistic)',
        line=dict(color='green', width=2, dash='dash')
    ))
    
    fig.add_trace(go.Scatter(
        x=x_axis,
        y=p50,
        mode='lines',
        name='P50 (Median)',
        line=dict(color='yellow', width=3)
    ))
    
    fig.add_trace(go.Scatter(
        x=x_axis,
        y=p5,
        mode='lines',
        name='P5 (Pessimistic)',
        line=dict(color='red', width=2, dash='dash')
    ))
    
    fig.update_layout(
        title='Monte Carlo Simulation (Bootstrap Resampling)',
        yaxis_title='Equity ($) [Log Scale]',
        xaxis_title='Trade Number',
        template='plotly_dark',
        height=600
    )
    
    fig.update_yaxes(type="log", autorange=True)
    
    return fig

def plot_price_history(df: pd.DataFrame, ticker: str) -> go.Figure:
    """
    Plot historical price data with range selector.
    """
    # 1. Create Figure
    fig = go.Figure()

    # 2. Add Candlestick Trace
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=ticker
    ))

    # Calculate default zoom range (last 30 days)
    if not df.empty:
        last_date = df.index.max()
        first_date = last_date - pd.Timedelta(days=30)
        initial_range = [first_date, last_date]
    else:
        initial_range = None

    # 3. Update X-axes Range Selector (Button Styling)
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=5, label="5D", step="day", stepmode="backward"),
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(count=5, label="5Y", step="year", stepmode="backward"),
                dict(step="all", label="All")
            ]),
            font=dict(color="white", size=12),
            bgcolor="#333333",
            activecolor="#FF4B4B",
            bordercolor="#555555",
            borderwidth=1
        ),
        range=initial_range
    )

    # 4. Update Layout (Global Level - Disable Slider & Set Title)
    # CRITICAL: xaxis_rangeslider_visible=False must be here to prevent Y-axis locking
    fig.update_layout(
        title=f"{ticker} Price History",
        yaxis_title='Price',
        xaxis_title='Date',
        template='plotly_dark',
        height=600,
    dragmode='pan',
        xaxis_rangeslider_visible=False
    )

    # 5. Force Y-Axis Auto-Scaling
    fig.update_yaxes(
        autorange=True,
        fixedrange=False
    )

    return fig

def plot_monthly_heatmap(equity_curve: pd.Series) -> go.Figure:
    """
    Plot Monthly Returns Heatmap.
    """
    if equity_curve.empty:
        return go.Figure()

    # 1. Calculate Monthly Returns
    monthly_returns = equity_curve.resample('ME').last().pct_change().fillna(0)
    
    # 2. Create Pivot Table (Year x Month)
    # We need to handle cases where data might not start in Jan or end in Dec
    monthly_returns.index = pd.to_datetime(monthly_returns.index)
    df = pd.DataFrame({'return': monthly_returns})
    df['year'] = df.index.year
    df['month'] = df.index.month
    
    pivot_table = df.pivot(index='year', columns='month', values='return')
    
    # Fill missing months with NaN (so they show as empty/gray)
    # Ensure all months 1-12 exist
    for m in range(1, 13):
        if m not in pivot_table.columns:
            pivot_table[m] = np.nan
            
    # Sort columns 1-12
    pivot_table = pivot_table.reindex(columns=range(1, 13))
    # Sort rows descending (newest year on top)
    pivot_table = pivot_table.sort_index(ascending=False)
    
    # 3. Prepare Data for Heatmap
    z = pivot_table.values
    x = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    y = pivot_table.index.tolist()
    
    # Text for cells
    text = np.round(z * 100, 2)
    text_template = []
    for row in text:
        row_text = []
        for val in row:
            if np.isnan(val):
                row_text.append("")
            else:
                row_text.append(f"{val:+.2f}%")
        text_template.append(row_text)
        
    # 4. Plot
    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=x,
        y=y,
        text=text_template,
        texttemplate="%{text}",
        textfont={"size": 10},
        colorscale='RdYlGn', # Red-Yellow-Green
        zmid=0, # Center color scale at 0
        colorbar=dict(title='Return', tickformat='.0%'),
        xgap=1, # Gap between cells
        ygap=1
    ))
    
    fig.update_layout(
        title='Monthly Returns Heatmap',
        xaxis_title='Month',
        yaxis_title='Year',
        template='plotly_dark',
        height=400 + (len(y) * 20), # Dynamic height based on number of years
        yaxis=dict(dtick=1) # Show every year
    )
    
    return fig