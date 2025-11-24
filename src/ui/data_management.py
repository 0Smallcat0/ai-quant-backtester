import streamlit as st
import time
import pandas as pd
from datetime import datetime
from src.ui.plotting import plot_price_history

def render_data_management_page(dm):
    """
    Renders the Data Management page (Market Data Center).
    
    Args:
        dm: DataManager instance.
    """
    st.title("📊 Market Data Center")
    
    # --- Zone 1: Watchlist Management (Top) ---
    with st.expander("📋 Watchlist Management", expanded=True):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Add Ticker
            new_ticker = st.text_input("Add Ticker Symbol", placeholder="e.g., AAPL, 2330, BTC", key="dm_add_ticker")
            if st.button("Add to Watchlist", type="primary"):
                try:
                    normalized = dm.normalize_ticker(new_ticker)
                    dm.add_to_watchlist(normalized)
                    st.success(f"Added **{normalized}** to watchlist.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
        
        with col2:
            # Remove Ticker
            watchlist = dm.get_watchlist()
            if watchlist:
                st.write(f"**Total Tracked:** {len(watchlist)}")
                to_remove = st.multiselect("Remove Tickers", watchlist, key="dm_remove_ticker")
                if to_remove:
                    if st.button("Confirm Removal"):
                        for t in to_remove:
                            dm.remove_from_watchlist(t)
                        st.success(f"Removed {len(to_remove)} tickers.")
                        st.rerun()
            else:
                st.info("Watchlist is empty.")

    # --- Zone 2: Operations & Status (Middle) ---
    st.markdown("---")
    st.subheader("🔄 Data Operations")
    
    # Date Selection
    d_col1, d_col2 = st.columns(2)
    with d_col1:
        start_date = st.date_input("Start Date", value=pd.to_datetime("2020-01-01"))
    with d_col2:
        end_date = st.date_input("End Date", value=datetime.today())
    
    col_op1, col_op2 = st.columns([1, 3])
    
    with col_op1:
        if st.button("🚀 Update All Data", type="primary", width="stretch"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(progress, message):
                progress_bar.progress(progress)
                status_text.text(message)
                
            with st.spinner("Batch updating watchlist..."):
                dm.update_all_tracked_symbols(
                    progress_callback=update_progress,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )
            
            st.success("All data updated successfully!")
            time.sleep(1)
            progress_bar.empty()
            status_text.empty()
            
    with col_op2:
        # Status Summary (Optional - could be expanded)
        if watchlist:
            st.info(f"Ready to update {len(watchlist)} symbols in your watchlist.")
        else:
            st.warning("Add symbols to watchlist to start tracking data.")

    # --- Zone 3: Data Preview (Bottom) ---
    st.markdown("---")
    st.subheader("📈 Data Preview")
    
    watchlist = dm.get_watchlist()
    if watchlist:
        selected_ticker = st.selectbox("Select Ticker to View", watchlist, index=0, key="dm_preview_select")
        
        # Fetch Data
        df = dm.get_data(selected_ticker)
        
        if not df.empty:
            # Display Metrics
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            change = latest['Close'] - prev['Close']
            pct_change = (change / prev['Close']) * 100
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Close Price", f"{latest['Close']:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
            m2.metric("Volume", f"{latest['Volume']:,}")
            m3.metric("Date", str(latest.name.date()))
            m4.metric("Records", len(df))
            
            # Simple Chart
            tab1, tab2 = st.tabs(["Chart", "Raw Data"])
            
            with tab1:

                fig = plot_price_history(df, selected_ticker)
                st.plotly_chart(fig, width="stretch")
                
            with tab2:
                st.dataframe(df.sort_index(ascending=False))
        else:
            st.warning(f"No data found for {selected_ticker}. Please run 'Update All Data'.")
    else:
        st.info("Add tickers to watchlist to view data.")
