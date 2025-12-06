import time
import pytest
import pandas as pd
import numpy as np
import os
from src.backtest_engine import BacktestEngine
from src.data_engine import DataManager

class TestPerformanceBenchmark:
    @pytest.fixture
    def large_dataset(self):
        """Create a 10,000 candle random dataset"""
        dates = pd.date_range(start='2020-01-01', periods=10000, freq='D')
        data = pd.DataFrame({
            'open': np.random.rand(10000) * 100,
            'high': np.random.rand(10000) * 100,
            'low': np.random.rand(10000) * 100,
            'close': np.random.rand(10000) * 100,
            'volume': np.random.randint(1000, 100000, 10000)
        }, index=dates)
        # Ensure high is highest and low is lowest
        data['high'] = data[['open', 'close', 'high']].max(axis=1)
        data['low'] = data[['open', 'close', 'low']].min(axis=1)
        return data

    @pytest.fixture
    def dummy_signals(self, large_dataset):
        """Create dummy signals for the dataset"""
        signals = pd.Series(
            np.random.choice([-1, 0, 1], size=len(large_dataset)),
            index=large_dataset.index,
            name='signal'
        )
        return signals

    def test_benchmark_backtest_speed(self, large_dataset, dummy_signals):
        """Benchmark A: Backtest Speed"""
        engine = BacktestEngine(initial_capital=100000.0)
        start_time = time.time()
        engine.run(large_dataset, dummy_signals)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"\n[Benchmark A] Backtest 10k candles: {duration:.4f} seconds")
        
        # We expect it to be reasonably fast, but the goal is relative improvement.
        # For now, just assert it runs.
        assert duration > 0

    def test_benchmark_db_write_speed(self, tmp_path):
        """Benchmark B: DB Write Speed"""
        db_path = tmp_path / "bench_test.db"
        engine = DataManager(db_path=str(db_path))
        engine.init_db()
        
        # Create 1000 tickers data
        data = []
        for i in range(1000):
            data.append({
                'ticker': 'AAPL',
                'date': f'2023-01-{i%30+1:02d}',
                'open': 100.0,
                'high': 105.0,
                'low': 95.0,
                'close': 102.0,
                'volume': 10000
            })
        
        df = pd.DataFrame(data)
        
        start_time = time.time()
        engine.save_data(df, 'AAPL')
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"\n[Benchmark B] DB Write 1000 records: {duration:.4f} seconds")
        
        assert duration > 0
