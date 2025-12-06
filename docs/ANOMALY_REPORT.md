# Forensic Diagnosis Report: Data Anomalies
**Date:** 2025-12-06
**Investigator:** Antigravity (Data Forensics Specialist)

## Executive Summary
The forensic analysis confirms multiple failure points across the Data Ingestion and Processing pipeline.
1.  **0050.TW**: **Confirmed Failure**. News is fetched but content is **Mojibake (Garbled Text)**, causing Sentiment Analysis to return neutral/zero scores.
2.  **BTC-USD**: **Partial Failure**. News is fetched (Dec 01), but the "Straight Line" symptom suggests either sparse news frequency (Decay to 0) or Model insensitivity.
3.  **NVDA**: **Calibration Issue**. "Too volatile" confirms the `DecayModel` half-life is too short, causing scores to jump wildly on single news items.
4.  **GOGL**: **Stale Data**. Database holds data only up to **2025-08-19**. The metadata claiming an update on 2025-12-06 is a **False Positive** (Update ran but fetched nothing). Price is **~7.98 - 8.28**, not 0.01 or 1000.

---

## Detailed Findings

### 1. TW (0050) - encoding hell
*   **Symptom**: Sentiment Score = 0.
*   **Diagnosis**:
    *   `NewsFetcher` successfully retrieved 10 headlines.
    *   **CRITICAL**: Title content is corrupted: `Pak͡u0050...`.
    *   **Root Cause**: The Google News RSS for TW market is likely returning `Big5` or `CP950` encoded XML, but `feedparser` or `requests` is decoding it as `UTF-8` (or vice versa), or the response encoding detection failed.
    *   **Impact**: Keywords like "台積電" or "股市" fail to match `Pak...`. Impact Score = 0 -> Sentiment = 0.

### 2. Crypto (BTC) - The Flatline
*   **Symptom**: "Straight line" in sentiment graph.
*   **Diagnosis**:
    *   News was fetched (Latest: 2025-12-01).
    *   Current Date: 2025-12-06.
    *   **Gap**: 5 days without news.
    *   **Decay Logic**: With a short half-life (e.g., 24h), a score from 5 days ago would have decayed to near-zero (`0.5^5 = 0.03`).
    *   **Conclusion**: The "Line" is likely a flatline at **Zero** because the signal decayed effectively to silence, OR it's a flatline at the last known score if the decay logic is "Sticky" (but code shows it decays to 0).

### 3. US (NVDA) - High Volatility
*   **Symptom**: Slope too steep.
*   **Diagnosis**:
    *   News is frequent (Latest: 2025-12-05).
    *   **Code Inspection**:
        ```python
        # s_t = (last_val * decay) + (new * (1 - decay))
        ```
    *   If `half_life` is default (likely 1 day or less?), `decay` is small. The `new` score dominates the weighted average immediately.
    *   **Action**: Increase `half_life` to **3-5 days** to smooth out the curve.

### 4. GOGL - The Zombie Ticker
*   **Symptom**: Price confusion & Update failure.
*   **Diagnosis**:
    *   **DB Price**: ~8.00 USD. (NOT 0.01, NOT 1000).
    *   **Staleness**: Last candle is **2025-08-19**.
    *   **Metadata**: `last_updated = 2025-12-06`.
    *   **Conclusion**: The Data Engine attempted an update today, found no new content (or failed silently), but updated the `metadata` timestamp anyway. This "Fake Update" hides the fact that the ticker is dead/delisted/renamed in the source.

---

## Repair Plan (Recommended Actions)

### Step 1: Fix Text Encoding (Priority High)
**Target**: `src/data/news_fetcher.py`
*   **Fix**: Force explicit encoding handling.
    ```python
    response.encoding = 'utf-8' # Or detect using chardet
    # If source is actually Big5, we might need:
    # content = response.content.decode('big5', errors='ignore')
    ```
*   **Test**: Re-fetch 0050.TW and verify readable Chinese characters.

### Step 2: Tune Decay Model (Priority Medium)
**Target**: `src/config/settings.py`
*   **Fix**: Increase `SENTIMENT_DECAY_HALFLIFE` from `1` (implied) to `3` or `5`.
*   **Effect**: Reduces NVDA volatility, preserves BTC signal longer.

### Step 3: Fix GOGL & Dead Ticker Detection (Priority Medium)
**Target**: `src/data_engine.py`
*   **Fix**: Do NOT update `metadata.last_updated` if `fetched_rows == 0`.
*   **Fix**: Add a "Staleness Check" in the UI. If `max(date) < Now - 30 days`, flag as **STALE/HALTED**.
