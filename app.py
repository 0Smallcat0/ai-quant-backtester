import streamlit as st
from src.data_engine import DataManager


from src.config.settings import settings

# Page Config
st.set_page_config(
    page_title="AI Quant Engine",
    page_icon="📈",
    layout="wide"
)

from src.ui.settings import render_global_settings_page

# Initialize Components
@st.cache_resource
def get_data_manager():
    dm = DataManager(db_path=str(settings.DB_PATH))
    dm.init_db()
    return dm

dm = get_data_manager()
# llm_client initialization removed to prevent startup crash. 
# It will be initialized lazily in specific pages or components.

# --- Sidebar Navigation & Global Settings ---
st.sidebar.title("🧭 Navigation")
page = st.sidebar.radio("Go to", ["Home", "Data Management", "Strategy & Backtest", "AI Developer Agent", "Global Settings"])

st.sidebar.markdown("---")

# --- Page: Home ---
if page == "Home":
    st.title(f"🤖 AI-Driven Quantitative Backtesting Engine ({settings.VERSION})")
    st.markdown("""
    Welcome to the **AI Quant Engine**. This platform allows you to:
    
    *   **Manage Data**: Fetch and store market data locally.
    *   **Design Strategies**: Use AI or Python code to define trading logic.
    *   **Backtest**: Simulate strategies with T+1 execution and advanced analytics.
    *   **Global Settings**: Configure API keys and models.
    """)
    
    st.info("👈 Select a page from the sidebar to get started.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 System Status")
        st.success("System Online")
        st.write(f"**Database Path:** `{settings.DB_PATH}`")
        
    with col2:
        st.subheader("🚀 Quick Start")
        st.write("1. Go to **Global Settings** to set your API Key.")
        st.write("2. Go to **Data Management** to fetch data.")
        st.write("3. Go to **Strategy & Backtest** to run a simulation.")

# --- Page: Data Management ---
elif page == "Data Management":
    from src.ui.data_management import render_data_management_page
    render_data_management_page(dm)

# --- Page: Strategy & Backtest ---
elif page == "Strategy & Backtest":
    from src.ui.strategy_creation import render_strategy_creation_page
    render_strategy_creation_page(dm)

# --- Page: Global Settings ---
elif page == "Global Settings":
    render_global_settings_page(dm)

# --- Page: AI Developer Agent ---
elif page == "AI Developer Agent":
    from src.ui.agent_chat import render_agent_chat_page
    render_agent_chat_page(dm)
