# AI-Driven Quantitative Backtesting Engine (v1.1)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)

## Introduction

This is a professional-grade **Quantitative Backtesting System** integrated with **LLM-driven Sentiment Analysis**. Unlike traditional backtesters that rely solely on price action, this engine combines rigorous financial logic (T+1 execution, bankruptcy protection) with real-time news impact analysis to simulate how market sentiment affects trading strategies.

## ✨ New Features in v1.1

### 📰 News Sentiment Engine
## Features (v1.1)

### 1. Multi-Source Data Engine
- **Sources**: Yahoo Finance (Global), Stooq (Global), TwStock (Taiwan), CCXT (Crypto).
- **Resilience**: Automatic failover and retry logic.
- **Verification Mode**: "FULL_VERIFY" mode to ensure data integrity before backtesting.

### 2. Advanced Sentiment Engine v2.0
- **Relevance Weighting**: Distinguishes between high-impact news (Earnings) and noise (Gossip).
- **Superposition Decay**: Linear superposition algorithm handles overlapping news events correctly.
- **LLM Integration**: Uses OpenAI GPT-4o for semantic analysis.

### 3. Dynamic Strategy Engine
- **Position Sizing**: Dynamic sizing based on sentiment strength (Risk-On/Risk-Off).
- **Presets**: Built-in strategies (SentimentRSI, MovingAverage, BollingerBreakout).
- **Backtest Engine**: Event-driven engine with Target-Delta execution and bankruptcy protection.

### 4. Professional UI
- **Streamlit Dashboard**: Interactive charts, logs, and configuration.
- **Real-time Logs**: Streaming execution logs for transparency.

### ⚙️ Robust Architecture
*   **SSOT Configuration**: All critical parameters (Keywords, Timezones, Risk Limits) are centralized in `src/config/settings.py`.
*   **Strict Backtesting**: 
    *   **Target-Delta Execution**: Prevents "Zombie Shorts" and infinite leverage bugs.
    *   **Bankruptcy Protection**: Automatically halts trading if equity hits zero.
    *   **Long-Only Compliance**: Enforced at the engine level for spot markets.

### 🛡️ Data Sources & Resilience
The engine implements a robust **Provider Pattern** with cascading failover to ensure data availability across global markets.

| Market | Primary Source | Failover/Backup |
| :--- | :--- | :--- |
| **US Stocks** | YFinance | Stooq (via pandas-datareader) |
| **Taiwan Stocks** | YFinance | TwStock (Official TWSE/TPEX) |
| **Crypto** | YFinance | CCXT (Binance/Kraken) |

**Key Features:**
*   **Automatic Failover**: If the primary source fails, the engine automatically detects the asset class and switches to the appropriate backup provider.
*   **Standardized Output**: All providers are strictly audited to return data with consistent columns (`Open`, `High`, `Low`, `Close`, `Volume`) and types.
*   **Rate Limiting**: Built-in protection for sensitive APIs (e.g., TwStock) to prevent IP bans.

## ⚠️ Known Limitations

> **Historical Data Limitation**
> The News Sentiment Engine relies on **live RSS feeds**. Historical backtests (e.g., 2020-2023) will default to **Neutral Sentiment (0.0)** due to the unavailability of historical RSS data. This feature is optimized for **Live Monitoring** and **Paper Trading**.

## 🚀 Quick Start

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Configuration
Copy the example environment file and set your OpenAI API Key:
```bash
cp .env.example .env
# Edit .env and add your API_KEY
```

### 3. Launch
Start the Streamlit dashboard:
```bash
streamlit run app.py
```

---
*Built with ❤️ by the AI Quant Team*
