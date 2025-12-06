import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from src.config.settings import settings

def render_dashboard(json_path: str = "backtest_results.json"):
    """
    Renders the Institution-Grade Dashboard from a JSON result file.
    """
    st.title("📊 AI Quant Backtest Dashboard (v2.0)")
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        st.warning(f"No results found at {json_path}. Run a backtest first.")
        return

    # 1. Header Metrics (Health & Weather)
    
    # [STRICT V2.0 HANDSHAKE]
    if data.get('version') != "2.0":
        st.error(f"Backend Version Mismatch: Expected v2.0, got {data.get('version', 'Unknown')}. Please update your backend/CLI.")
        st.stop()

    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
    
    # Extract Data
    metrics = data.get('metrics', {})
    health = data.get('health_check', {})
    weather = data.get('market_weather', {})
    
    with metrics_col1:
        st.metric("Total Return", f"{metrics.get('Total Return (%)', 0):.2f}%")
    with metrics_col2:
        st.metric("Sharpe Ratio", f"{metrics.get('Sharpe Ratio', 0):.2f}")
    with metrics_col3:
        st.metric("Max Drawdown", f"{metrics.get('Max Drawdown (%)', 0):.2f}%")
    with metrics_col4:
        # WFA Score / Health
        wfa_score = health.get('wfa_score', 'N/A')
        st.metric("WFA Score", str(wfa_score), help="Walk-Forward Analysis Stability Score")

    # 2. Market Weather & Insight
    st.divider()
    w_col1, w_col2 = st.columns([1, 2])
    
    with w_col1:
        st.subheader("🌤️ Market Weather")
        regime = weather.get('regime', 'Unknown')
        color_map = {
            'Bull': 'green',
            'Bear': 'red',
            'Sideways': 'yellow'
        }
        color = color_map.get(regime, 'grey')
        st.markdown(f"<h2 style='color: {color};'>{regime}</h2>", unsafe_allow_html=True)
        st.caption(f"VIX: {weather.get('vix', 'N/A')} | ADX: {weather.get('adx', 'N/A')}")
        
    with w_col2:
        st.subheader("💡 AI Insight")
        # [BINDING] Strict binding to market_weather['insight']
        insight_text = weather.get('insight', 'No insight available.')
        st.info(insight_text)
        
    # 3. Equity Curve
    st.divider()
    st.subheader("📈 Equity Curve")
    equity_data = data.get('equity_curve', [])
    if equity_data:
        df_eq = pd.DataFrame(equity_data)
        df_eq['date'] = pd.to_datetime(df_eq['date'])
        
        fig = px.line(df_eq, x='date', y='equity', title='Portfolio Equity')
        st.plotly_chart(fig, use_container_width=True)
        
    # 4. Trades Analysis
    st.divider()
    with st.expander("📋 Trade Log & Analysis"):
        trades = data.get('trades', [])
        if trades:
            df_trades = pd.DataFrame(trades)
            st.dataframe(df_trades)
            
            # Win Rate Visualization
            win_rate = metrics.get('Win Rate (%)', 0)
            fig_pie = px.pie(names=['Win', 'Loss'], values=[win_rate, 100-win_rate], title="Win/Loss Ratio")
            st.plotly_chart(fig_pie)
        else:
            st.info("No trades executed.")

    # 5. Configuration View
    with st.expander("⚙️ Backtest Configuration"):
        st.json(data.get('config', {}))
