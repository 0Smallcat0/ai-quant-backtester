# AI-Driven Quantitative Backtesting Engine 使用手冊

歡迎使用 **AI 驅動量化回測引擎**！這是一個輕量級、開源的本地端回測工具，專為希望結合 AI 輔助與傳統程式碼撰寫策略的交易者設計。

本手冊將引導您完成安裝、設定、數據獲取、策略制定及回測分析。

---

## 1. 安裝與啟動 (Installation)

### 1.1 環境需求
請確保您的電腦已安裝 **Python 3.10 或更高版本**。

### 1.2 安裝依賴套件
在專案資料夾中打開終端機 (Terminal) 或命令提示字元 (Command Prompt)，執行以下指令：

```bash
pip install -r requirements.txt
```

### 1.3 設定 API 金鑰 (選用)
如果您想使用 **AI 策略助理 (Text-to-Code)** 功能，您需要一組 OpenAI API Key。
1.  將 `.env.example` 檔案重新命名為 `.env`。
2.  使用文字編輯器打開 `.env`，填入您的金鑰：
    ```
    OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx
    ```

### 1.4 啟動程式
執行以下指令來啟動網頁介面：

```bash
streamlit run app.py
```
啟動後，瀏覽器應會自動打開 `http://localhost:8501`。

---

## 2. 系統介面概覽

### 左側邊欄 (Settings)
*   **Ticker**: 輸入股票或加密貨幣代碼 (例如 `AAPL`, `TSLA`, `BTC-USD`)。
*   **Start Date / End Date**: 設定回測的日期範圍。
*   **Initial Capital**: 設定初始資金 (美金)。
*   **Fetch/Update Data 按鈕**: 點擊此按鈕可從 Yahoo Finance 下載或更新最新的市場數據到本地資料庫。

### 主畫面 (Main Area)
*   **Strategy Definition**: 定義您的交易策略。
*   **Run Backtest 按鈕**: 執行回測。
*   **Backtest Results**: 顯示回測結果、圖表與交易明細。

---

## 3. 使用流程教學

### 步驟一：獲取數據
1.  在左側邊欄輸入您想回測的標的 (例如 `NVDA`)。
2.  點擊 **"Fetch/Update Data"**。
3.  系統會顯示 "Data for NVDA is ready!" 表示數據已存入本地資料庫。

### 步驟二：定義策略 (兩種模式)

#### 模式 A：AI 助理 (適合初學者/快速原型)
1.  選擇 **"AI Assistant (Natural Language)"**。
2.  在文字框中用英文描述您的策略。
    *   範例 1: *"Buy when RSI < 30, Sell when RSI > 70"* (RSI 低於 30 買進，高於 70 賣出)
    *   範例 2: *"Buy when price is above SMA(200), Sell when price is below SMA(200)"* (價格高於 200均線買進，低於則賣出)
3.  點擊 **"Generate Code"**。AI 會自動生成對應的 Python 程式碼並顯示在下方。

#### 模式 B：程式碼編輯器 (適合進階使用者)
1.  選擇 **"Code Editor (Python)"**。
2.  直接編輯 Python 程式碼。您必須定義一個繼承自 `Strategy` 的類別，並實作 `generate_signals` 方法。
    ```python
    class MyStrategy(Strategy):
        def generate_signals(self, df: pd.DataFrame) -> pd.Series:
            # 1 = Buy, -1 = Sell, 0 = Hold
            signals = pd.Series(0, index=df.index)
            # 您的邏輯...
            return signals
    ```

### 步驟三：執行回測
1.  確認策略無誤後，點擊主畫面的 **"🚀 Run Backtest"** 按鈕。
2.  系統將進行運算 (包含 T+1 交易執行模擬)。

---

## 4. 解讀回測報告

### 4.1 績效指標 (Metrics)
*   **Final Equity**: 最終資產總值。
*   **Total Return**: 總報酬率。
*   **Sharpe Ratio (夏普比率)**: 衡量每單位風險所獲得的超額報酬 (越高越好，>1 為佳)。
*   **Max Drawdown (最大回撤)**: 資產從高點滑落的最大幅度 (越小越好)。

### 4.2 互動式圖表 (Interactive Chart)
*   **K線圖**: 顯示股價走勢。
*   **綠色箭頭 (▲)**: 買進訊號 (Buy)。
*   **紅色箭頭 (▼)**: 賣出訊號 (Sell)。
*   **藍色線圖**: 資產權益曲線 (Equity Curve)。
*   *提示：您可以使用滑鼠滾輪縮放圖表，或將游標移至數據點查看詳細資訊。*

### 4.3 蒙地卡羅模擬 (Monte Carlo Simulation)
系統會隨機重組每日報酬率 1000 次，以評估策略的穩健性。
*   **95% Worst Case (VaR)**: 在 95% 的情況下，您的最終資產不會低於此數值 (風險底線)。
*   **Median Outcome**: 模擬的中位數結果。

### 4.4 交易明細 (Trade Log)
點擊 **"📜 Trade Log"** 展開詳細的交易紀錄，包含每筆交易的日期、價格、股數與損益。

---

## 5. 常見問題 (FAQ)

**Q: 為什麼交易是在訊號出現的「隔天」才執行？**
A: 這是為了避免「前視偏誤 (Look-ahead Bias)」。在真實世界中，您通常是在收盤後確認訊號，並在隔天開盤時進行交易。本系統嚴格遵守 **T+1 Open** 執行邏輯，以確保回測結果的真實性。

**Q: 數據存放在哪裡？**
A: 數據存放在專案目錄下的 `data/market_data.db` (SQLite 資料庫)。您可以隨時刪除此檔案以重置數據。

**Q: AI 生成的程式碼報錯怎麼辦？**
A: AI 偶爾會生成語法錯誤的程式碼。您可以切換到 **"Code Editor"** 模式手動修正，或嘗試用更精確的語言重新描述您的策略。

---

**祝您交易順利！ 🚀**
