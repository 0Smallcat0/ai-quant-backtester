import streamlit as st
import time
import pandas as pd
import re
from datetime import datetime
from src.ui.plotting import plot_price_history

def _categorize_tickers(watchlist):
    categories = {
        'TW': [],
        'US': [],
        'Crypto': [],
        'Other': []
    }
    
    for ticker in watchlist:
        # TW: 4 digits at start or ends with .TW
        if (ticker[:4].isdigit() and len(ticker) >= 4) or ticker.endswith('.TW'):
            categories['TW'].append(ticker)
        # Crypto: Contains -USD
        elif '-USD' in ticker:
            categories['Crypto'].append(ticker)
        # US: All uppercase, no - or . (basic check)
        elif ticker.isupper() and '-' not in ticker and '.' not in ticker:
            categories['US'].append(ticker)
        else:
            categories['Other'].append(ticker)
            
    # Sorting
    def tw_sort_key(t):
        match = re.match(r"(\d+)", t)
        if match:
            return int(match.group(1))
        return float('inf')
        
    categories['TW'].sort(key=tw_sort_key)
    categories['US'].sort()
    categories['Crypto'].sort()
    categories['Other'].sort()
    
    return categories

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
                if not new_ticker.strip():
                    st.error("⚠️ Ticker symbol cannot be empty!")
                else:
                    try:
                        normalized = dm.normalize_ticker(new_ticker)
                        dm.add_to_watchlist(normalized)
                        st.success(f"Added **{normalized}** to watchlist.")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
        
        with col2:
            # Remove Ticker (Categorized)
            watchlist = dm.get_watchlist()
            if watchlist:
                # Categorize
                cats = _categorize_tickers(watchlist)
                
                # Summary Metrics
                total = len(watchlist)
                tw_count = len(cats['TW'])
                us_count = len(cats['US'])
                crypto_count = len(cats['Crypto'])
                
                st.write(f"**Total:** {total} (TW:{tw_count}, US:{us_count}, Cryp:{crypto_count})")
                
                # Tabs
                tabs = st.tabs(["TW", "US", "Cryp", "Oth"])
                
                # Helper to render removal list
                def render_removal_list(category_name, tickers, key_suffix):
                    if not tickers:
                        st.caption(f"No {category_name} tickers.")
                        return
                    
                    to_remove = st.multiselect(
                        f"Remove {category_name}", 
                        tickers, 
                        key=f"remove_{key_suffix}",
                        label_visibility="collapsed"
                    )
                    if to_remove:
                        if st.button(f"Remove Selected", key=f"btn_remove_{key_suffix}"):
                            for t in to_remove:
                                dm.remove_from_watchlist(t)
                            st.success(f"Removed {len(to_remove)} tickers.")
                            st.rerun()

                with tabs[0]:
                    render_removal_list("TW", cats['TW'], "tw")
                with tabs[1]:
                    render_removal_list("US", cats['US'], "us")
                with tabs[2]:
                    render_removal_list("Crypto", cats['Crypto'], "crypto")
                with tabs[3]:
                    render_removal_list("Other", cats['Other'], "other")
                    
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
        # Categorize
        cats = _categorize_tickers(watchlist)
        
        # Category Filter
        category_options = ["All", "TW", "US", "Crypto", "Other"]
        selected_category = st.radio("Filter by Category", category_options, horizontal=True, key="dm_preview_cat")
        
        # Filter Tickers
        if selected_category == "All":
            # Combine all sorted lists
            filtered_watchlist = cats['TW'] + cats['US'] + cats['Crypto'] + cats['Other']
        else:
            filtered_watchlist = cats[selected_category]
            
        if not filtered_watchlist:
            st.warning(f"No tickers found in category '{selected_category}'.")
            return

        selected_ticker = st.selectbox("Select Ticker to View", filtered_watchlist, index=0, key="dm_preview_select")
        
        # Fetch Data
        df = dm.get_data(selected_ticker)
        
        if not df.empty:
            # Display Metrics
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            change = latest['close'] - prev['close']
            pct_change = (change / prev['close']) * 100
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Close Price", f"{latest['close']:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
            m2.metric("Volume", f"{latest['volume']:,}")
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
