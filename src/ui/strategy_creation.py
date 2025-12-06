import streamlit as st
import pandas as pd
import traceback
from src.ai.llm_client import LLMClient
# [FIX] Use the engineered Agent System Prompt
from src.ai.prompts_agent import AGENT_SYSTEM_PROMPT as SYSTEM_PROMPT
from src.strategies.loader import StrategyLoader, StrategyLoadError
from src.backtest_engine import BacktestEngine
from src.strategies.manager import StrategyManager
from src.config.settings import settings
from src.analytics.performance import calculate_cagr, calculate_max_drawdown, calculate_sharpe_ratio, calculate_win_rate

def render_strategy_creation_page(dm):
    st.header("AI Strategy Creator & Backtester")

    # [Fail Fast] Check Watchlist
    try:
        watchlist = dm.get_watchlist()
    except Exception as e:
        st.error(f"Error fetching watchlist: {e}")
        watchlist = []

    if not watchlist:
        st.warning("⚠️ **No Data Available**")
        st.info("您的關注清單 (Watchlist) 目前是空的。請先前往 **Data Management** 頁面新增標的並更新數據，才能開始回測。")
        st.stop()

    # --- 1. Backtest Settings ---
    with st.expander("⚙️ Backtest Settings", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        available_tickers = watchlist
        
        # Filter Ticker by Category
        from src.utils import categorize_ticker
        filter_cat = st.radio(
            "Filter Ticker by Category:", 
            ["All", "TW", "US", "Crypto", "Other"], 
            horizontal=True
        )
        
        if filter_cat != "All":
            filtered_tickers = [t for t in available_tickers if categorize_ticker(t) == filter_cat]
        else:
            filtered_tickers = available_tickers
            
        filtered_tickers.sort()
        
        ticker = col1.selectbox("Select Ticker", filtered_tickers)
        start_date = col2.date_input("Start Date", value=pd.to_datetime("2023-01-01"))
        end_date = col3.date_input("End Date", value=pd.to_datetime("today"))
        
        # Load defaults from global settings if available
        global_settings = st.session_state.get('trading_settings', {})
        
        # Initialize Session State for Strategy Creation (sc_) if not present
        if 'sc_initial_capital' not in st.session_state:
            st.session_state['sc_initial_capital'] = float(global_settings.get('initial_capital', settings.INITIAL_CAPITAL))
        if 'sc_commission_rate' not in st.session_state:
            st.session_state['sc_commission_rate'] = float(global_settings.get('commission_rate', settings.COMMISSION_RATE))
        if 'sc_slippage' not in st.session_state:
            st.session_state['sc_slippage'] = float(global_settings.get('slippage', settings.SLIPPAGE))
        if 'sc_min_commission' not in st.session_state:
            st.session_state['sc_min_commission'] = float(global_settings.get('min_commission', settings.MIN_COMMISSION))
        
        c1, c2, c3 = st.columns(3)
        initial_capital = c1.number_input("Initial Capital ($)", min_value=100.0, key="sc_initial_capital", step=100.0)
        commission_rate = c2.number_input("Commission Rate (0.001 = 0.1%)", min_value=0.0, key="sc_commission_rate", step=0.0001, format="%.4f")
        slippage = c3.number_input("Slippage (0.001 = 0.1%)", min_value=0.0, key="sc_slippage", step=0.0001, format="%.4f")
        
        c4, c5 = st.columns(2)
        min_commission = c4.number_input("Min Commission ($)", min_value=0.0, key="sc_min_commission", step=0.5)
        long_only_mode = c5.checkbox("Long Only (No Shorting)", value=True, help="If checked, the strategy will not take short positions.")

    # --- 2. Strategy Definition ---
    st.subheader("🧠 Strategy Definition")
    
    # Initialize Session State
    if "generated_code" not in st.session_state:
        st.session_state.generated_code = ""
    if "strategy_description" not in st.session_state:
        st.session_state.strategy_description = "RSI < 30 and Sentiment >= 0 Buy, RSI > 70 Sell"
    if "strategy_mode" not in st.session_state:
        st.session_state.strategy_mode = "Preset Strategy"

    # Mode Selection
    mode = st.radio("Select Strategy Mode", ["Preset Strategy", "AI Assistant", "Python Script"], horizontal=True, key="strategy_mode_selection")
    st.session_state.strategy_mode = mode

    strategy_to_run = None
    code_to_run = None
    preset_name = None
    preset_params = {}

    if mode == "Preset Strategy":
        st.markdown("### Choose a Preset Strategy")
        
        manager = StrategyManager()
        custom_strategies = manager.list_all()
        system_presets = ["MovingAverageStrategy", "SentimentRSIStrategy"]
        all_strategies = system_presets + custom_strategies
        
        preset_name = st.selectbox("Strategy Type", all_strategies)
        
        if preset_name in custom_strategies:
            st.info(f"Custom Strategy: {preset_name}")
            if st.button("🗑️ Delete Preset"):
                manager.delete(preset_name)
                st.success(f"Deleted {preset_name}")
                st.rerun()
        
        if preset_name == "MovingAverageStrategy":
            preset_params['window'] = st.number_input("Window Size", min_value=1, value=settings.DEFAULT_MA_WINDOW)
        elif preset_name == "SentimentRSIStrategy":
            c1, c2, c3 = st.columns(3)
            preset_params['period'] = c1.number_input("RSI Period", min_value=1, value=settings.DEFAULT_RSI_PERIOD)
            preset_params['buy_threshold'] = c2.number_input("Buy Threshold", min_value=1, max_value=100, value=settings.DEFAULT_RSI_BUY_THRESHOLD)
            preset_params['sell_threshold'] = c3.number_input("Sell Threshold", min_value=1, max_value=100, value=settings.DEFAULT_RSI_SELL_THRESHOLD)
            
    elif mode == "AI Assistant":
        col_input, col_code = st.columns([1, 1])
        with col_input:
            st.markdown("### Describe Strategy")
            description = st.text_area(
                "Natural Language Description",
                value=st.session_state.strategy_description,
                height=300,
                help="Describe your strategy logic here. The AI will generate code for you."
            )
            
            if st.button("✨ Generate Code"):
                with st.spinner("AI is thinking..."):
                    try:
                        client = LLMClient()
                        full_prompt = f"{SYSTEM_PROMPT}\n\nUser Description: {description}"
                        raw_code = client.generate_strategy_code(full_prompt)
                        cleaned_code = client.clean_code(raw_code)
                        st.session_state.generated_code = cleaned_code
                        # Sync the widget key as well to ensure it updates
                        st.session_state['ai_code_editor'] = cleaned_code
                        st.success("Code generated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error generating code: {e}")
                    
        with col_code:
            st.markdown("### Strategy Code")
            code_to_run = st.text_area(
                "Python Code (Editable)",
                value=st.session_state.generated_code,
                height=300,
                key="ai_code_editor"
            )
            st.session_state.generated_code = code_to_run

    elif mode == "Python Script":
        st.markdown("### Write Python Code")
        code_to_run = st.text_area(
            "Python Code",
            value=st.session_state.generated_code if st.session_state.generated_code else "from src.strategies.base import Strategy\nimport pandas as pd\n\nclass MyStrategy(Strategy):\n    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:\n        # Implement your logic here\n        pass",
            height=400,
            key="script_code_editor"
        )
        st.session_state.generated_code = code_to_run

        st.markdown("#### Save Strategy")
        col_name, col_save = st.columns([3, 1])
        with col_name:
            strategy_name = st.text_input("Strategy Name", placeholder="MyCustomStrategy")
        with col_save:
            st.write("") # Spacer
            st.write("") # Spacer
            if st.button("💾 Save to Presets"):
                if not strategy_name:
                    st.error("Please enter a strategy name.")
                elif not code_to_run or not code_to_run.strip():
                    st.error("Cannot save empty code.")
                else:
                    manager = StrategyManager()
                    manager.save(strategy_name, code_to_run)
                    st.success(f"Strategy '{strategy_name}' saved!")
                    # Force rerun to update presets list immediately
                    st.rerun()

    # --- 3. Execution ---
    st.markdown("---")
    
    # Initialize backtest_results in session state if not present
    if "backtest_results" not in st.session_state:
        st.session_state.backtest_results = None

    if st.button("🚀 Run Backtest", type="primary"):
        
        with st.spinner("Running Backtest..."):
            try:
                # 1. Load Strategy
                loader = StrategyLoader()
                
                if mode == "Preset Strategy":
                    manager = StrategyManager()
                    custom_code = manager.get(preset_name)
                    
                    if custom_code:
                        strategy = loader.load_from_code(custom_code)
                    else:
                        strategy = loader.load_preset(preset_name, **preset_params)
                else:
                    if not code_to_run or not code_to_run.strip():
                        st.warning("Please generate or write some code first.")
                        return
                    strategy = loader.load_from_code(code_to_run)
                

                
                # [SAFETY] Date Validation
                if pd.to_datetime(start_date) >= pd.to_datetime(end_date):
                    st.error("Start Date must be strictly before End Date.")
                    return

                df = dm.get_data(ticker, include_sentiment=True)
                if df.empty:
                    st.error(f"No data found for {ticker}.")
                    return
                
                # Filter Data
                mask = (df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))
                df = df.loc[mask]
                
                if df.empty:
                    st.error("No data in the selected date range.")
                    return

                # --- Data Sanity Check ---
                # 1. Gap Detection
                # Calculate difference between consecutive dates
                date_diff = df.index.to_series().diff()
                # Check for gaps > 5 days (approx 1 week)
                gaps = date_diff[date_diff > pd.Timedelta(days=5)]
                
                if not gaps.empty:
                    st.warning(f"⚠️ **Data Quality Warning**: Detected {len(gaps)} gaps of more than 5 days in the data. "
                               "This might indicate missing data or long trading halts, which can affect backtest accuracy.")
                    with st.expander("View Data Gaps"):
                        st.write(gaps)

                # 2. Missing/Zero Value Check & Fix
                cols_to_check = ['open', 'high', 'low', 'close']
                # Check if any 0 or NaN exists
                has_zeros = (df[cols_to_check] == 0).any().any()
                has_nans = df[cols_to_check].isna().any().any()
                
                if has_zeros or has_nans:
                    st.warning("⚠️ **Data Quality Warning**: Found missing (NaN) or Zero values in OHLC data. "
                               "Attempting to patch with forward-fill.")
                    
                    # Replace 0 with NaN, then ffill, then fillna(0) as last resort
                    df[cols_to_check] = df[cols_to_check].replace(0, np.nan).ffill().fillna(method='bfill')
                    
                    # Re-check
                    if (df[cols_to_check].isna().any().any()):
                         st.error("❌ Critical Data Error: Unable to patch all missing values. Please check data source.")
                         return
                # -------------------------

                # 3. Run Engine
                # Load Global Settings (Sizing only, others from UI)
                trading_settings = st.session_state.get('trading_settings', {
                    'sizing_method': 'Fixed Percentage (%)',
                    'sizing_target': 95.0
                })
                
                engine = BacktestEngine(
                    initial_capital=initial_capital, 
                    commission_rate=commission_rate, 
                    slippage=slippage,
                    min_commission=min_commission,
                    long_only=long_only_mode
                )
                
                # Apply Position Sizing
                method_map = {
                    'Fixed Percentage (%)': 'fixed_percent',
                    'Fixed Amount ($)': 'fixed_amount'
                }
                method_key = method_map.get(trading_settings['sizing_method'], 'fixed_percent')
                
                target = trading_settings['sizing_target']
                if method_key == 'fixed_percent':
                    # Convert 95.0 to 0.95
                    engine.set_position_sizing(method_key, target=target/100.0)
                else:
                    engine.set_position_sizing(method_key, amount=target)
                
                # Generate Signals
                # Normalize columns to lowercase to prevent KeyError in AI strategies
                df_for_strategy = df.copy()
                df_for_strategy.columns = [c.lower() for c in df_for_strategy.columns]
                
                signals_df = strategy.generate_signals(df_for_strategy)
                
                # Check if 'signal' column exists
                # [FIX] Protocol Adapter: Convert AI Triggers to Signals
                if 'entries' in signals_df.columns and 'exits' in signals_df.columns:
                    st.info("⚙️ Detected AI Trigger Strategy: Applying Thick Engine Latching...")
                    # Convert Triggers to State (0/1)
                    from src.backtest.thick_engine import apply_latching_engine
                    position_state = apply_latching_engine(signals_df['entries'], signals_df['exits'])
                    # Cast bool to int (1 for Hold, 0 for Flat)
                    signals_df['signal'] = position_state.astype(int)

                if 'signal' not in signals_df.columns:
                    st.error("Strategy did not return a DataFrame with a 'signal' column.")
                    return
                
                # Run Engine with signals
                engine.run(df, signals_df['signal'])
                
                # --- 4. Performance Analysis ---
                equity_curve = pd.DataFrame(engine.equity_curve)
                equity_curve.set_index('date', inplace=True)
                
                # Calculate Metrics
                
                start_val = initial_capital
                end_val = equity_curve['equity'].iloc[-1]
                years = (equity_curve.index[-1] - equity_curve.index[0]).days / 365.25
                if years == 0: years = 0.001
                
                cagr = calculate_cagr(start_val, end_val, years)
                mdd = calculate_max_drawdown(equity_curve['equity'])
                
                returns = equity_curve['equity'].pct_change().fillna(0)
                sharpe = calculate_sharpe_ratio(returns)
                
                # Calculate Win Rate (FIFO Matching)
                trades = engine.trades
                pnl_list = []
                buy_queue = [] # List of [price, qty]
                
                for trade in trades:
                    if trade.type == 'BUY':
                        buy_queue.append([trade.entry_price, trade.quantity])
                    elif trade.type == 'SELL':
                        qty_to_sell = trade.quantity
                        sell_price = trade.entry_price
                        
                        trade_pnl = 0
                        while qty_to_sell > 0 and buy_queue:
                            buy_item = buy_queue[0] # FIFO
                            buy_price = buy_item[0]
                            buy_qty = buy_item[1]
                            
                            matched_qty = min(qty_to_sell, buy_qty)
                            
                            # PnL = (Sell Price - Buy Price) * Qty
                            trade_pnl += (sell_price - buy_price) * matched_qty
                            
                            qty_to_sell -= matched_qty
                            buy_item[1] -= matched_qty
                            
                            if buy_item[1] <= 0:
                                buy_queue.pop(0)
                        
                        pnl_list.append(trade_pnl)
                
                win_rate = calculate_win_rate(pd.Series(pnl_list))
                
                # Store results in session state
                st.session_state.backtest_results = {
                    "cagr": cagr,
                    "mdd": mdd,
                    "sharpe": sharpe,
                    "win_rate": win_rate,
                    "equity_curve": equity_curve,
                    "df": df,
                    "trades": trades,
                    "initial_capital": initial_capital
                }
                
                st.success("Backtest Complete!")

            except StrategyLoadError as e:
                st.error(f"Strategy Load Error: {e}")
                return
            except Exception as e:
                st.error(f"Runtime Error: {e}\n{traceback.format_exc()}")
                return

    # --- Display Results (if available) ---
    if st.session_state.backtest_results:
        results = st.session_state.backtest_results
        
        # Display Metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        
        # --- Benchmark Calculations ---
        # Benchmark Equity (Buy & Hold)
        bench_series = results['df']['close']
        bench_start = bench_series.iloc[0]
        bench_end = bench_series.iloc[-1]
        
        # CAGR
        # Recalculate years from stored equity curve
        equity_curve = results['equity_curve']
        years = (equity_curve.index[-1] - equity_curve.index[0]).days / 365.25
        if years == 0: years = 0.001
        
        bench_cagr = calculate_cagr(bench_start, bench_end, years)
        
        # MDD
        # Reconstruct benchmark equity curve starting from initial_capital for fair MDD calc (though % is same)
        bench_equity_curve = (bench_series / bench_start) * initial_capital
        bench_mdd = calculate_max_drawdown(bench_equity_curve)
        
        # Sharpe
        bench_returns = bench_series.pct_change().fillna(0)
        bench_sharpe = calculate_sharpe_ratio(bench_returns)
        
        # --- Metrics with Delta ---
        m1.metric(
            "CAGR", 
            f"{results['cagr']:.2%}", 
            delta=f"{results['cagr'] - bench_cagr:.2%}",
            help=f"Benchmark CAGR: {bench_cagr:.2%}"
        )
        
        m2.metric(
            "Max Drawdown", 
            f"{results['mdd']:.2%}", 
            delta=f"{results['mdd'] - bench_mdd:.2%}",
            help=f"Benchmark MDD: {bench_mdd:.2%}"
        )
        
        m3.metric(
            "Sharpe Ratio", 
            f"{results['sharpe']:.2f}", 
            delta=f"{results['sharpe'] - bench_sharpe:.2f}",
            help=f"Benchmark Sharpe: {bench_sharpe:.2f}"
        )
        
        m4.metric("Win Rate", f"{results['win_rate']:.2%}")
        
        # Calculate Avg Exposure
        # Exposure = Position Value / Equity
        if 'position_value' in results['equity_curve'].columns:
             # We need to ensure we don't divide by zero. Equity should not be zero usually.
             results['equity_curve']['exposure'] = results['equity_curve']['position_value'] / results['equity_curve']['equity']
             avg_exposure = results['equity_curve']['exposure'].mean()
             m5.metric("Avg. Exposure", f"{avg_exposure:.1%}", help="Average capital deployed in the market. Low value (<20%) means 'Cash Drag'.")
        else:
             m5.metric("Avg. Exposure", "N/A")
        
        # Display Charts
        from src.ui.plotting import plot_trading_chart, plot_equity_curve, plot_monthly_heatmap
        
        st.subheader("📈 Equity Curve")
        fig_equity = plot_equity_curve(results['equity_curve'], benchmark_equity=results['df'])
        st.plotly_chart(fig_equity, width="stretch")
        
        st.subheader("📅 Monthly Returns")
        # Pass the equity series
        fig_heatmap = plot_monthly_heatmap(results['equity_curve']['equity'])
        st.plotly_chart(fig_heatmap, width="stretch")
        
        st.subheader("🕯️ Trading Signals")
        fig_trading = plot_trading_chart(results['df'], results['trades'])
        st.plotly_chart(fig_trading, width="stretch")
        

        # Trade Log
        # Auto-expand if trade count is low to help diagnosis
        expand_log = len(results['trades']) < 50
        with st.expander("📋 Trade Log", expanded=expand_log):
            trade_data = []
            for t in results['trades']:
                trade_data.append({
                    "Date": t.entry_date,
                    "Type": t.type,
                    "Price": t.entry_price,
                    "Quantity": t.quantity,
                    "Value": t.entry_price * t.quantity,
                    "Commission": max(t.entry_price * t.quantity * commission_rate, min_commission) # Estimate
                })
            st.dataframe(pd.DataFrame(trade_data))

        # --- 5. Monte Carlo Simulation ---
        st.markdown("---")
        st.subheader("🎲 Monte Carlo Simulation")
        
        if st.button("Run Monte Carlo Analysis"):
            with st.spinner("Running 1000 Simulations..."):
                # Calculate Trade Returns % for Monte Carlo
                # Calculate Trade Returns % for Monte Carlo
                # We need (Exit - Entry) / Entry for each trade cycle
                # Use the robust FIFO matcher from performance module
                from src.analytics.performance import calculate_round_trip_returns
                
                # Fetch settings for Monte Carlo
                # Use the local variable 'commission_rate' from the Backtest Settings widget directly
                # No need to re-fetch from session state as we have the most up-to-date value here

                mc_trade_returns = calculate_round_trip_returns(results['trades'], commission_rate=commission_rate)
                
                # --- Debug & Sanity Check ---
                if mc_trade_returns:
                    avg_mc_return = sum(mc_trade_returns) / len(mc_trade_returns)
                    
                    # Debug Output
                    with st.expander("🔍 Monte Carlo Input Debug (FIFO Matched Returns)"):
                        st.write(f"Total Round-Trip Trades: {len(mc_trade_returns)}")
                        st.write(f"Average Return per Trade (Portfolio Weighted): {avg_mc_return:.4%}")
                        st.write("First 5 Returns:", mc_trade_returns[:5])
                        
                        if avg_mc_return > 0 and results['cagr'] < 0:
                             st.warning("⚠️ **Data Consistency Warning**: Backtest CAGR is negative, but average trade return is positive. "
                                        "This might be due to compounding effects, commissions, or holding periods, "
                                        "but please verify your strategy logic.")
                        
                        if abs(avg_mc_return) < 0.001:
                            st.info("ℹ️ **Note**: Average return per trade is very small (< 0.1%). "
                                    "This is expected if you are using small position sizing (Portfolio-Weighted Returns).")
                # ----------------------------
                
                if not mc_trade_returns:
                    st.warning("Not enough trades to run Monte Carlo simulation.")
                else:
                    from src.analytics.monte_carlo import run_monte_carlo_simulation
                    from src.ui.plotting import plot_monte_carlo_simulation
                    
                    # Explicit Normalization for UI Layer
                    # If mean absolute return > 1.0, assume percentage (e.g. 5.0) and divide by 100
                    mc_series = pd.Series(mc_trade_returns)
                    if mc_series.abs().mean() > 1.0:
                        mc_trade_returns = (mc_series / 100.0).tolist()
                    
                    mc_results = run_monte_carlo_simulation(mc_trade_returns, n_simulations=1000, initial_capital=results['initial_capital'])
                    
                    # Helper for Human Readable Numbers
                    def format_currency_human(value):
                        abs_val = abs(value)
                        if abs_val >= 1e12:
                            return f"${value/1e12:.2f}T"
                        elif abs_val >= 1e9:
                            return f"${value/1e9:.2f}B"
                        elif abs_val >= 1e6:
                            return f"${value/1e6:.2f}M"
                        elif abs_val >= 1e3:
                            return f"${value/1e3:.2f}K"
                        else:
                            return f"${value:,.2f}"

                    # Sanity Check Warning
                    p50_final = mc_results['p50'][-1]
                    backtest_final_equity = results['equity_curve']['equity'].iloc[-1]
                    
                    # Check for Order of Magnitude Difference
                    if p50_final > backtest_final_equity * 10:
                         st.warning(f"⚠️ **Simulation Discrepancy**: Monte Carlo P50 Result (${p50_final:,.0f}) is significantly higher than Backtest Result (${backtest_final_equity:,.0f}). "
                                    "This often happens if the simulation assumes full compounding but the backtest used fixed sizing. "
                                    "We have updated the logic to use Portfolio-Weighted Returns to mitigate this, but please double check.")

                    if p50_final > results['initial_capital'] * 50:
                        st.warning("⚠️ 異常高回報警示 (Unrealistic Return Warning)\n\n"
                                   "此策略在模擬中產生了極高的回報 (超過 50 倍)。"
                                   "在現實市場中，這通常意味著：\n"
                                   "- 策略使用了未來數據 (Look-ahead Bias)。\n"
                                   "- 忽略了流動性限制或市場衝擊。\n"
                                   "- 數據源存在錯誤。\n\n"
                                   "請仔細檢查您的策略邏輯。")

                    # Display Stats
                    c1, c2, c3 = st.columns(3)
                    
                    # Smart VaR Display & Context-Aware Metrics
                    p5_final = mc_results['p5_final']
                    initial_cap = results['initial_capital']
                    
                    if p5_final > initial_cap:
                         # Profitable Scenario (Worst case is still profit)
                         st_var_label = "Worst Case Profit (P5)"
                         st_var_val = format_currency_human(p5_final - initial_cap)
                    else:
                         # Loss Scenario
                         st_var_label = "Value at Risk (95%)"
                         st_var_val = format_currency_human(mc_results['var_95_amount'])
                    
                    c1.metric(st_var_label, st_var_val)
                    c2.metric("Median Drawdown", f"{mc_results['median_drawdown']:.2%}")
                    c3.metric("P5 Final Equity", format_currency_human(p5_final))
                    
                    # Display Plot
                    fig_mc = plot_monte_carlo_simulation(mc_results)
                    st.plotly_chart(fig_mc, width="stretch")

