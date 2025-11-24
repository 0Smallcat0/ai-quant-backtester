# AI-Driven Quantitative Backtesting Engine

![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)

## Introduction

The **AI-Driven Quantitative Backtesting Engine** is a professional-grade research platform designed to bridge the gap between **Large Language Model (LLM) intelligence** and **rigorous financial simulation**. 

## 🔥 Key Features

### 1. Financial Realism & Safety
*   **Target-Delta Execution**: Eliminates "Infinite Leverage" bugs by calculating the exact delta required to reach a target portfolio percentage.
*   **Strict Long-Only Mode**: Mathematically proven prevention of short selling in long-only portfolios.
*   **Bankruptcy Protection**: Immediate simulation termination if equity hits zero, preventing unrealistic recovery from ruin.
*   **T+1 Execution**: Signals generated on Day T (Close) are strictly executed on Day T+1 (Open) to prevent lookahead bias.

### 2. AI-Assisted Strategy Development
*   **Natural Language to Code**: Generate valid Python strategies using OpenAI/OpenRouter integration.
*   **Anti-Lookahead Guard**: AI-generated code is sanitized with regex to block future data access (e.g., `shift(-1)`).
*   **Atomic Write Protection**: Strategies are saved using atomic operations to prevent file corruption during edits.

### 3. Advanced Analytics
*   **Portfolio-Weighted Monte Carlo**: Simulates thousands of market scenarios using Log Scale returns for accurate long-term compounding projection.
*   **Transaction Cost Simulation**: Configurable commission and slippage models.
*   **Smart Metrics**: CAGR, Sharpe Ratio, Sortino Ratio, and Max Drawdown calculated on Portfolio Equity (not just trade capital).

## 🚀 Quick Start

### Prerequisites
*   Python 3.9+
*   Git

### Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/0Smallcat0/ai-quant-backtester.git
    cd ai-quant-backtester
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**
    Copy the example environment file and add your API keys (OpenAI/OpenRouter).
    ```bash
    cp .env.example .env
    ```

4.  **Run the Application**
    ```bash
    streamlit run app.py
    ```

## Development

We follow a strict **Search Before Create** philosophy to maintain code hygiene.

*   **Read the Protocol**: Please review [CONTRIBUTING.md](CONTRIBUTING.md) before making changes.
*   **Test-Driven Development (TDD)**: All new features must start with a failing test in `tests/`.
*   **Code Style**: We prioritize readability and explicit variable names over clever one-liners.

