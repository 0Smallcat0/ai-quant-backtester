import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Mock Data Generation
def get_mock_data():
    dates = pd.date_range(end=datetime.today(), periods=500)
    # Create a trend that changes significantly over time to test Y-axis scaling
    prices = np.linspace(100, 200, 500) + np.random.normal(0, 5, 500)
    # Add a spike at the end
    prices[-50:] = prices[-50:] * 1.5 
    
    df = pd.DataFrame({
        'open': prices + np.random.normal(0, 1, 500),
        'high': prices + np.random.normal(2, 1, 500),
        'low': prices - np.random.normal(2, 1, 500),
        'close': prices
    }, index=dates)
    return df

def plot_price_history(df: pd.DataFrame, ticker: str) -> go.Figure:
    """
    Plot historical price data with range selector (Copied from src/ui/plotting.py for standalone testing)
    """
    fig = go.Figure()

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

    fig.update_layout(
        title=f"{ticker} Price History",
        yaxis_title='Price',
        xaxis_title='Date',
        template='plotly_dark',
        height=600,
        dragmode='pan',
        xaxis_rangeslider_visible=False
    )

    # Force Y-Axis Auto-Scaling
    fig.update_yaxes(
        autorange=True,
        fixedrange=False
    )

    return fig

st.title("🧪 Manual Plot Test")
st.write("Test the Range Selector and Y-Axis Auto-Scaling.")

df = get_mock_data()
fig = plot_price_history(df, "MOCK-TEST")

st.plotly_chart(
    fig, 
    use_container_width=True,
    config={
        'scrollZoom': True, 
        'displayModeBar': True,
        'modeBarButtonsable': ['zoom2d', 'pan2d', 'resetScale2d', 'autoScale2d']
    }
)

st.info("Instructions: Click '1M', '6M', 'All' buttons. Verify Y-axis rescales to fit the data visible in that range.")
