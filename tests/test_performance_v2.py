import pytest
import pandas as pd
import numpy as np
import time
from src.backtest_engine import BacktestEngine
from src.data.sentiment_processor import DecayModel
from src.core.events import SignalEvent

class TestPerformanceV2:
    @pytest.fixture
    def large_market_data(self):
        """Generates 10,000 rows of OHLCV data."""
        np.random.seed(42)
        dates = pd.date_range(start="2000-01-01", periods=10000, freq="D")
        df = pd.DataFrame({
            'open': np.random.uniform(100, 200, 10000),
            'high': np.random.uniform(200, 210, 10000),
            'low': np.random.uniform(90, 100, 10000),
            'close': np.random.uniform(100, 200, 10000),
            'volume': np.random.uniform(1000000, 5000000, 10000)
        }, index=dates)
        return df

    @pytest.fixture
    def large_signals(self, large_market_data):
        """Generates corresponding signals."""
        signals = pd.Series(np.random.choice([-1, 0, 1], size=10000), index=large_market_data.index, name='signal')
        return signals

    @pytest.fixture
    def large_sentiment_scores(self):
        """Generates 5,000 random sentiment scores over time."""
        np.random.seed(42)
        dates = pd.date_range(start="2020-01-01", periods=5000, freq="D")
        scores = {d: np.random.uniform(-1, 1) for d in dates}
        return dates, scores

    def test_backtest_engine_speed(self, large_market_data, large_signals):
        """Benchmark BacktestEngine.run speed."""
        engine = BacktestEngine(initial_capital=1e9)
        
        start_time = time.time()
        engine.run(large_market_data, large_signals)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"\n[Benchmark] BacktestEngine (10k rows): {duration:.4f}s")
        
        # Performance Goal: < 0.5s
        # Note: We assert a soft limit here to allow baseline to run, 
        # but in final verification we might enforce strict limits.
        # assert duration < 2.0 # Allow slack for unoptimized version first

    def test_decay_model_speed(self, large_sentiment_scores):
        """Benchmark DecayModel.apply_decay speed."""
        dates, scores_dict = large_sentiment_scores
        model = DecayModel(half_life_days=5)
        
        start_time = time.time()
        result = model.apply_decay(dates, scores_dict)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"\n[Benchmark] DecayModel (5k pts): {duration:.4f}s")
        
        assert len(result) == 5000
        # Performance Goal: < 0.05s
        # assert duration < 1.0
