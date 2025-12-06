Contributing to AI-Driven Quantitative Backtesting Engine
Welcome to the development team! This project adheres to strict engineering standards to ensure financial accuracy, system stability, and AI safety.

Please read these protocols carefully before contributing code or asking the AI Agent to make changes.

1. Core Philosophy: "Search Before Create"
Goal: Prevent code duplication and maintain a Single Source of Truth (SSOT).

Step 1 (Search): Before implementing any function (e.g., RSI calculation), use grep or the AI Agent's list_files to check if it already exists.

Step 2 (Reuse): If a similar function exists, import and use it.

Step 3 (Refactor): If it exists but lacks a feature, refactor the existing function rather than creating a _v2 or _new version.

Step 4 (Create): Only create new files if the functionality is distinctly new.

Step 5 (Clean): When modifying logic, actively identify and remove "Dead Code" (unused variables, old parameters, or commented-out blocks).

2. Financial Logic & Mathematics (CRITICAL)
Goal: Prevent "Fantasy Backtests" and numerical errors.

2.1 Precision & Types
Floating Point Only: All prices, quantities, and capital must be handled as float.

Reason: To support high-priced assets (e.g., Bitcoin) where fractional shares (0.001 BTC) are necessary. Never cast quantity to int.

Zero Division Protection: Always assume a denominator can be zero. Use guards:

Python

if price <= 0: return 0.0
result = amount / (price + 1e-9) # or explicit check
2.2 Backtesting Integrity (Anti-Cheat)
No Look-ahead Bias:

Signals generated on Day T (Close) must be executed on Day T+1 (Open).

Forbidden: df['close'].shift(-1) or accessing current day's close for execution price.

Bankruptcy Protection:

Pre-Trade: Always check cost <= available_cash before executing a BUY.

Liquidation: If Equity <= 0, the backtest loop must break immediately. Negative equity is impossible in Spot trading.

Target-Delta Execution:

Do not separate BUY/SELL logic blindly. Calculate Target Position first, then derive the Delta (Trade Quantity). This prevents the "Infinite Leverage/Zombie Short" bug.

2.3 Portfolio-Weighted Returns
When calculating metrics for Monte Carlo, calculate returns based on Portfolio Equity, not just Trade Capital.

Correct: (PnL / Total_Account_Equity)

Incorrect: (PnL / Trade_Cost) -> This leads to unrealistic exponential growth simulations.

3. Development Workflow (TDD)
Goal: Ensure stability across refactors.

Red (Write Test): Create a test case in tests/ that reproduces the bug or defines the new feature. Run it to confirm it fails.

Green (Implement): Write the minimal code in src/ to pass the test.

Refactor: Optimize the code without breaking the test.

Verify: Run pytest to ensure no regressions in other modules.

Integration Check: (New!) If adding a parameter, verify the UI actually controls it (see Section 7).

4. UI & Visualization Guidelines (Streamlit/Plotly)
Goal: Consistent UX and bug-free rendering.

Session State: Streamlit reruns the script on every interaction. Use st.session_state to persist variables (e.g., chat history, backtest results) across reruns.

Fail Fast: Check for empty data (e.g., Watchlist) at the top of the render function. Use st.stop() to prevent rendering broken UI components.

Plotly Charts:

Candlestick Y-Axis Fix: Always set xaxis_rangeslider_visible=False in fig.update_layout. The default range slider locks the Y-axis scaling, making charts unreadable on zoom.

Log Scale: Use Log Scale for Monte Carlo simulations to visualize exponential growth properly.

5. AI Agent Security Protocols
Goal: Prevent the AI from destroying the system.

Human-in-the-Loop: All sensitive tools (write_file, run_shell) MUST return a PendingAction object and require explicit user approval via the UI.

Stateless Shell: The run_shell tool is stateless. cd commands do not persist. Chain commands using &&.

Input Sanitization: The AI Agent must use the specialized AGENT_SYSTEM_PROMPT which forbids future data access patterns (e.g., negative shifts) in generated code.

6. Data Management
Lowercase Columns: The BacktestEngine expects lowercase column names (open, close). Always normalize DataFrame columns immediately after fetching or loading:

Python

df.columns = [c.lower() for c in df.columns]
Resource Cleanup: Always close database connections, preferably using with context managers or try...finally blocks.

7. Configuration & Parameter Synchronization (SSOT)
Goal: Prevent "Phantom Parameters" (UI settings that do not affect the backend).

7.1 Single Source of Truth
Definition: src/config/settings.py is the only place where configuration constants (e.g., DEFAULT_SLIPPAGE, DEFAULT_COMMISSION) are defined.

Prohibition: Do not hardcode magic numbers (e.g., commission=0.001) inside BacktestEngine or UI files. Import them from settings.py.

7.2 Strict UI/Backend Mapping
1:1 Correspondence: If you add a parameter to BacktestEngine.__init__ (e.g., slippage), you MUST immediately update the instantiation call in src/ui/strategy_creation.py (or app.py).

Naming Convention: Use consistent variable names across the stack.

Bad: UI uses slippage_rate, Backend uses slippage.

Good: UI uses slippage, Backend uses slippage.

7.3 Sensitivity Testing (Mandatory)
Requirement: When introducing a new global parameter (e.g., Slippage), you must write a Sensitivity Test in tests/test_config_sensitivity.py.

Method: Run the backtest twice with different values for the parameter.

Assertion: Assert that Result_A != Result_B. If changing the parameter yields the exact same result, the feature is considered broken/disconnected.
