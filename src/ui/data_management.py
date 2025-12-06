import streamlit as st
import time
import pandas as pd
import re
from datetime import datetime
from src.ui.plotting import plot_price_history
from src.utils import detect_market
from src.data.news_fetcher import NewsFetcher

def _categorize_tickers(watchlist):
    categories = {
        'TW': [],
        'US': [],
        'Crypto': [],
        'Other': []
    }
    
    for ticker in watchlist:
        cat_raw = detect_market(ticker)
        # Map to display categories
        if cat_raw == 'CRYPTO':
            cat = 'Crypto'
        else:
            cat = cat_raw
        if cat in categories:
            categories[cat].append(ticker)
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

def _detect_market(ticker: str) -> str:
    """
    Simple helper to detect market type for news fetching.
    """
    if ticker.endswith('.TW') or ticker.endswith('.TWO'):
        return 'TW'
    elif '-' in ticker:
        return 'CRYPTO'
    else:
        return 'US'

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
            with st.form("add_ticker_form"):
                new_ticker = st.text_input("Add Ticker Symbol", placeholder="e.g., AAPL, 2330, BTC", key="dm_add_ticker")
                submitted = st.form_submit_button("Add to Watchlist", type="primary")
            
            if submitted:
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
        # [NEW] Update Strategy Selector
        update_strategy = st.radio(
            "Update Strategy",
            ["Smart Incremental (Fast)", "Full Verification (Strict)"],
            index=0,
            help="Smart: Only fetch new data. Full: Re-download all and vote on conflicts."
        )
        
        mode_map = {
            "Smart Incremental (Fast)": "INCREMENTAL",
            "Full Verification (Strict)": "FULL_VERIFY"
        }
        selected_mode = mode_map[update_strategy]
        
        if st.button("🚀 Update All Data", type="primary", width="stretch"):
            # Ensure News Engine exists
            if not getattr(dm, 'news_engine', None):
                # [OPTIMIZATION] Use cached resource for heavy model loading
                @st.cache_resource
                def get_news_engine():
                    from src.data.news_engine import NewsEngine
                    return NewsEngine()
                
                dm.news_engine = get_news_engine()

            # Phase 1: Price Update
            with st.status("🚀 Phase 1: 更新價格數據 (OHLCV)...", expanded=True) as status:
                progress_bar_p1 = st.progress(0)
                
                def update_progress(progress, message):
                    progress_bar_p1.progress(progress)
                    status.write(message)
                
                try:
                    dm.update_all_tracked_symbols(
                        progress_callback=update_progress,
                        start_date=start_date.strftime('%Y-%m-%d'),
                        end_date=end_date.strftime('%Y-%m-%d'),
                        update_mode=selected_mode
                    )
                except Exception as e:
                    error_msg = str(e)
                    if "DEAD_TICKER" in error_msg:
                         # Extract ticker if possible or just show message
                         match = re.search(r"DEAD_TICKER: (\S+)", error_msg)
                         ticker_name = match.group(1) if match else "Unknown"
                         st.error(f"⚠️ {ticker_name} 似乎已下市或代碼錯誤 (Yahoo 404)。建議從清單中移除。")
                    else:
                         st.error(f"Update failed: {e}")
                    # Stop execution of subsequent phases if Critical Error
                    st.stop()
                status.update(label="✅ 價格數據更新完成！", state="complete", expanded=False)

            # Phase 2: Sentiment Update (Smart Incremental)
            enable_sentiment = st.session_state.get('enable_sentiment', True)
            
            if enable_sentiment:
                with st.status("🧠 Phase 2: 分析市場情緒 (FinBERT + ABSA)...", expanded=True) as status_s:
                    st.caption("⚠️ 注意：新聞情緒分析僅支援『最近 30 天』的即時數據，無法回溯歷史。")
                    progress_bar_s = st.progress(0)
                    watchlist_s = dm.get_watchlist()
                    total_s = len(watchlist_s)
                    
                    if total_s > 0:
                        for i, ticker in enumerate(watchlist_s):
                            status_s.write(f"Checking {ticker} ({i+1}/{total_s})...")
                            # Use update_cache_smart logic
                            try:
                                dm.news_engine.update_cache_smart(ticker)
                            except Exception as e:
                                st.error(f"Error updating sentiment for {ticker}: {e}")
                            progress_bar_s.progress((i + 1) / total_s)
                    
                    status_s.write("All symbols updated.")
                    status_s.update(label="✅ 情緒分析完成！", state="complete", expanded=False)
            else:
                st.warning("⏩ Phase 2: 分析市場情緒 (已略過 - 請至 Global Settings 開啟)")
            
            st.success("所有數據更新完畢 (價格 + 情緒)！")
            
    with col_op2:
        # Status Summary (Optional - could be expanded)
        if watchlist:
            st.info(f"Ready to update {len(watchlist)} symbols in your watchlist.")
        else:
            st.warning("Add symbols to watchlist to start tracking data.")

    # --- Zone 3: Data Preview (Bottom) ---
    st.markdown("---")
    st.subheader("📈 Data Preview")
    
    # [OPTIMIZATION] Cached Data Fetcher for Preview
    @st.cache_data(ttl=600, show_spinner="Loading preview data...")
    def get_cached_data_preview(_dm, ticker: str):
         # Note: _dm starting with underscore prevents Streamlit from hashing the DataManager object
         return _dm.get_data(ticker)

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
        
        # Fetch Data (Cached)
        df = get_cached_data_preview(dm, selected_ticker)
        
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
            tab1, tab2, tab3 = st.tabs(["Chart", "Raw Data", "Sentiment"])
            
            with tab1:

                fig = plot_price_history(df, selected_ticker)
                st.plotly_chart(
                    fig, 
                    width="stretch",
                    config={
                        'scrollZoom': True, 
                        'displayModeBar': True,
                        'modeBarButtonsable': ['zoom2d', 'pan2d', 'resetScale2d', 'autoScale2d']
                    }
                )
                
            with tab2:
                st.dataframe(df.sort_index(ascending=False))
                
            with tab3:
                # Load Sentiment
                if not getattr(dm, 'news_engine', None):
                    from src.data.news_engine import NewsEngine
                    dm.news_engine = NewsEngine()
                
                import os
                # We need cache path. Since _get_cache_path is protected, we access it or duplicate logic.
                # Accessing protected member is acceptable here for UI.
                cache_path = dm.news_engine._get_cache_path(selected_ticker)
                
                if os.path.exists(cache_path):
                    try:
                        sent_df = pd.read_parquet(cache_path)
                        if not sent_df.empty:
                            st.caption("Sentiment Score (Decayed): Polarity over time")
                            # Normalize index to datetime just in case
                            sent_df.index = pd.to_datetime(sent_df.index)
                            
                            # [FIX] Smart Crop: Filter out near-zero noise and zoom to valid data
                            # Threshold = 0.001 to ignore float artifacts
                            significant_sentiment = sent_df[sent_df['sentiment'].abs() > 0.001]
                            
                            if not significant_sentiment.empty:
                                first_valid_idx = significant_sentiment.index.min()
                                # Buffer: 5 days before first valid data point
                                start_plot = first_valid_idx - pd.Timedelta(days=5)
                                sent_df = sent_df[start_plot:]
                            else:
                                # If all data is effectively zero, show a warning or just the tail
                                # st.warning("Only near-zero sentiment data found.")
                                pass # Proceed to plot what we have (likely flat 0s)
                                
                            st.line_chart(sent_df['sentiment'])
                            
                            st.divider()
                            st.write("Recent Raw Data (Top 5):")
                            st.dataframe(sent_df.sort_index(ascending=False).head(5))
                        else:
                            st.info("Sentiment data is empty.")
                    except Exception as e:
                        st.error(f"Error reading sentiment cache: {e}")
                else:
                    st.info(f"尚無情緒數據 ({selected_ticker})，請執行 Update All Data。")
                
            # [NEW] Live News Check
            st.divider()
            with st.expander("📰 最近 5 則新聞預覽 (Live Check)"):
                if st.button("取得最新新聞", key=f"btn_news_{selected_ticker}"):
                    with st.spinner("正在連線至 Google News RSS..."):
                        try:
                            market_type = _detect_market(selected_ticker)
                            fetcher = NewsFetcher()
                            news_items = fetcher.fetch_headlines(selected_ticker, market=market_type)
                            
                            if not news_items:
                                st.warning("⚠️ 查無新聞 (或是連線被阻擋)")
                            else:
                                # Only show top 5 as requested
                                for item in news_items[:5]:
                                    # 顯示標題與連結
                                    st.markdown(f"**[{item['title']}]({item['link']})**")
                                    st.caption(f"發布時間: {item.get('published', 'Unknown')}")
                                    st.divider()
                        except Exception as e:
                            st.error(f"新聞抓取失敗: {str(e)}")
                else:
                    st.info("點擊按鈕以測試新聞抓取功能")
        else:
            st.warning(f"No data found for {selected_ticker}. Please run 'Update All Data'.")
    else:
        st.info("Add tickers to watchlist to view data.")
