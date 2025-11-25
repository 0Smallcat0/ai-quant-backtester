# AI-Driven Quantitative Backtesting Engine (v1.0.0)

A professional-grade, event-driven backtesting engine designed for AI-generated trading strategies. It features strict financial realism, anti-lookahead architecture, and a modern Streamlit UI.

## 🔥 New Features in v1.1 (Stable)

*   **CLI Automation**: Run backtests directly from the terminal using `python src/run_backtest.py`.
*   **Dynamic Strategy Discovery**: Automatically detects and loads new strategy files in `src/strategies/`.
*   **Anti-Lookahead Architecture**: Enforces strict T+1 execution lag to prevent future data leakage.
*   **Realistic Execution**: Built-in Slippage, Commission models, and Bankruptcy protection.
*   **Single Source of Truth (SSOT)**: Centralized configuration in `src/config/settings.py`.

## 🚀 Quick Start

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Run the UI
```bash
streamlit run app.py
```
Navigate to **Data Management** to fetch data (e.g., `BTC-USD`), then **Strategy & Backtest** to run simulations.

### 3. Run via CLI (Automation)
```bash
# Run a preset strategy
python src/run_backtest.py --strategy_name MA_Crossover --ticker BTC-USD --start 2023-01-01

# Run a custom strategy (must exist in src/strategies/)
python src/run_backtest.py --strategy_name MyCustomStrategy --ticker ETH-USD
```

## 📚 Developer Guide

### Writing a Strategy
Create a new file in `src/strategies/` (e.g., `my_strategy.py`). Inherit from `Strategy` and implement `generate_signals`.

```python
from src.strategies.base import Strategy
import pandas as pd

class MyStrategy(Strategy):
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        # Use safe_rolling helper if available, or standard pandas
        df['ma'] = df['close'].rolling(20).mean()
        
        df['signal'] = 0
        df.loc[df['close'] > df['ma'], 'signal'] = 1 # Long
        
        return df
```

### Anti-Lookahead Rules
1.  **T+1 Execution**: Signals generated on Day T (using Close price) are executed on Day T+1 (Open price).
2.  **Forbidden Patterns**: The loader blocks code containing `.shift(-1)` or future slicing `iloc[i+1]`.

### Stress Testing
You can use the CLI to run stress tests by specifying different date ranges or tickers.
```bash
# Bull Market Stress Test
python src/run_backtest.py --strategy_name RSI_Strategy --start 2020-01-01 --end 2021-01-01

# Bear Market Stress Test
python src/run_backtest.py --strategy_name RSI_Strategy --start 2022-01-01 --end 2023-01-01
```

## 📂 Project Structure
```
.
├── app.py                  # Streamlit Entrypoint
├── src/
│   ├── backtest_engine.py  # Core Event-Driven Engine (T+1, Slippage)
│   ├── data_engine.py      # SQLite Data Management
│   ├── run_backtest.py     # CLI Entrypoint
│   ├── config/
│   │   └── settings.py     # SSOT Configuration
│   ├── strategies/
│   │   ├── base.py         # Abstract Base Class
│   │   ├── loader.py       # Dynamic Loader & Security Validator
│   │   └── presets.py      # Standard Strategies
│   └── ui/                 # Streamlit Components
└── tests/                  # Pytest Suite
```

## 🤝 Contributing
Please read `CONTRIBUTING.md` before submitting changes. We follow strict TDD and Financial Realism protocols.
