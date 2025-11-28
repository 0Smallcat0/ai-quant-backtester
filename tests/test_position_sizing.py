import pytest
import pandas as pd
import numpy as np
from src.strategies.sizing import SentimentSizer, PositionSizer

class TestSentimentSizer:
    
    def test_mapping_logic(self):
        """
        Test that sentiment scores map to correct weights.
        Formula: base * (0.5 + 0.5 * score)
        """
        sizer = SentimentSizer(base_weight=1.0, min_sentiment_threshold=0.2)
        
        # 1. High Sentiment (1.0) -> 1.0 * (0.5 + 0.5) = 1.0
        assert sizer.get_target_weight(1.0) == pytest.approx(1.0)
        
        # 2. Moderate Sentiment (0.5) -> 1.0 * (0.5 + 0.25) = 0.75
        assert sizer.get_target_weight(0.5) == pytest.approx(0.75)
        
        # 3. Threshold (0.2) -> 1.0 * (0.5 + 0.1) = 0.6
        assert sizer.get_target_weight(0.2) == pytest.approx(0.6)
        
        # 4. Below Threshold (0.1) -> 0.0
        assert sizer.get_target_weight(0.1) == pytest.approx(0.0)
        
        # 5. Negative Sentiment (-0.5) -> 0.0 (Risk Off)
        assert sizer.get_target_weight(-0.5) == pytest.approx(0.0)

    def test_scaling_factor(self):
        """
        Test with scale_factor > 1.0 (Leverage or Aggressive).
        """
        # Base 1.0, Scale 1.5
        # Formula: base * (0.5 + 0.5 * score) * scale ???
        # Wait, the user prompt said:
        # "scale_factor: 放大係數 (例如 1.0)"
        # "target_weight = base_weight * (0.5 + 0.5 * score)"
        # It didn't explicitly say where scale_factor goes in the formula.
        # Usually it multiplies the result.
        # Let's assume: weight = base * (mapping) * scale
        
        sizer = SentimentSizer(base_weight=1.0, min_sentiment_threshold=0.0, scale_factor=1.5)
        
        # Score 1.0 -> 1.0 * 1.0 * 1.5 = 1.5 (if allowed > 1.0)
        # But user said "Limit: [0.0, 1.0] (unless leverage enabled)"
        # Let's assume default is capped at 1.0.
        
        # Let's test a case that doesn't hit cap
        # Score 0.0 -> 1.0 * 0.5 * 1.5 = 0.75
        assert sizer.get_target_weight(0.0) == pytest.approx(0.75)

    def test_clipping(self):
        """
        Test that weight is clipped at 1.0 by default.
        """
        sizer = SentimentSizer(base_weight=2.0, min_sentiment_threshold=0.0)
        # Score 1.0 -> 2.0 * 1.0 = 2.0 -> Clipped to 1.0
        assert sizer.get_target_weight(1.0) == pytest.approx(1.0)

from src.backtest_engine import BacktestEngine

class TestBacktestIntegration:
    def test_target_size_execution(self):
        """
        Verify that BacktestEngine uses target_size from signals DataFrame.
        """
        # Setup data
        dates = pd.date_range(start="2023-01-01", periods=5, freq="D")
        data = pd.DataFrame({
            "open": [100.0, 100.0, 100.0, 100.0, 100.0],
            "high": [110.0, 110.0, 110.0, 110.0, 110.0],
            "low": [90.0, 90.0, 90.0, 90.0, 90.0],
            "close": [105.0, 105.0, 105.0, 105.0, 105.0],
            "volume": [1000, 1000, 1000, 1000, 1000]
        }, index=dates)
        
        # Setup signals with target_size
        # Day 0 Signal -> Executed Day 1 Open
        signals = pd.DataFrame(index=dates)
        signals['signal'] = 0
        signals['target_size'] = 0.0
        
        # Signal on Day 0: Buy with 0.5 size (50% equity)
        # Use iloc to set values
        signals.iloc[0, signals.columns.get_loc('signal')] = 1
        signals.iloc[0, signals.columns.get_loc('target_size')] = 0.5
        
        engine = BacktestEngine(initial_capital=10000.0)
        engine.run(data, signals)
        
        # Check Trade on Day 1
        # Entry Price = 100 (Open)
        # Equity ~ 10000
        # Target Exposure = 10000 * 0.5 = 5000
        # Qty = 5000 / 100 = 50
        
        assert len(engine.trades) >= 1
        trade = engine.trades[0]
        assert trade.entry_date == dates[1]
        # Allow small margin for slippage/commission calc in engine
        assert trade.quantity == pytest.approx(50.0, abs=1.0)

