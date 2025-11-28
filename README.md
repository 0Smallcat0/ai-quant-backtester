# AI-Driven Quantitative Backtesting Engine (v1.1)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)

## Introduction

This is a professional-grade **Quantitative Backtesting System** integrated with **LLM-driven Sentiment Analysis**. Unlike traditional backtesters that rely solely on price action, this engine combines rigorous financial logic (T+1 execution, bankruptcy protection) with real-time news impact analysis to simulate how market sentiment affects trading strategies.

## ✨ New Features in v1.1

### 📰 News Sentiment Engine
A sophisticated pipeline for real-time market intelligence:
*   **Multi-Source Aggregation**: Aggregates news from Google News RSS across **TW** (Taiwan), **US** (Wall St.), and **Crypto** markets.
*   **Funnel Filtering**: Automatically filters out noise (e.g., "Top 10 Stocks", "Market Wrap") to focus on actionable news.
*   **Impact Ranking (SSOT)**: 
    *   Prioritizes high-impact events like **Earnings (EPS)**, **Mergers**, and **Regulatory Actions**.
    *   Uses a weighted scoring algorithm configurable via `src/config/settings.py`.
*   **LLM Analysis**: Uses GPT-4 to summarize news and assign a sentiment score (-1.0 to +1.0).
*   **Exponential Decay**: Simulates the "memory" of the market with a 3-day half-life for sentiment scores.
*   **Timezone Alignment**: Handles global market hours and news rollover logic (e.g., post-market news affects the next trading day).

### 🧠 Sentiment-Weighted Strategies
*   **SentimentRSI**: An enhanced RSI strategy that adjusts entry/exit thresholds based on the aggregated sentiment score, preventing "buying the dip" during catastrophic news events.

### ⚙️ Robust Architecture
*   **SSOT Configuration**: All critical parameters (Keywords, Timezones, Risk Limits) are centralized in `src/config/settings.py`.
*   **Strict Backtesting**: 
    *   **Target-Delta Execution**: Prevents "Zombie Shorts" and infinite leverage bugs.
    *   **Bankruptcy Protection**: Automatically halts trading if equity hits zero.
    *   **Long-Only Compliance**: Enforced at the engine level for spot markets.

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
