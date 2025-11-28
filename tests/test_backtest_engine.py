import pytest
import pandas as pd
import numpy as np
from src.backtest_engine import BacktestEngine
from src.config.settings import settings

class TestBacktestEngine:
    @pytest.fixture
    def engine(self):
        return BacktestEngine()

    @pytest.fixture
    def sample_data(self):
        dates = pd.date_range(start="2023-01-01", periods=10)
        df = pd.DataFrame({
            'open': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
            'high': [105, 106, 107, 108, 109, 110, 111, 112, 113, 114],
            'low': [95, 96, 97, 98, 99, 100, 101, 102, 103, 104],
            'close': [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
            'volume': [1000] * 10
        }, index=dates)
        return df

    def test_initialization(self, engine):
        assert engine.initial_capital == settings.INITIAL_CAPITAL
        assert engine.commission_rate == settings.COMMISSION_RATE
        assert engine.slippage == settings.SLIPPAGE
        assert engine.current_capital == settings.INITIAL_CAPITAL
        assert engine.position == 0
        assert len(engine.trades) == 0

    def test_basic_run_long(self, engine, sample_data):
        # Buy on day 1 (executes day 2), Hold until day 5 (executes day 6)
        signals = pd.Series(0.0, index=sample_data.index)
        # Signal 1 means "Target 100% Long". 0 means "Flat".
        # To hold, we must maintain signal 1.
        signals.iloc[1:5] = 1.0 
        signals.iloc[5:] = 0.0
        
        engine.run(sample_data, signals)
        
        # Expect:
        # 1. Day 2: Buy (Signal 1 from Day 1)
        # 2. Intermediate days: Potential rebalancing trades (due to 95% target and price moves)
        # 3. Day 6: Sell (Signal 0 from Day 5)
        
        assert len(engine.trades) >= 2
        assert engine.trades[0].type == 'BUY'
        assert engine.trades[-1].type == 'SELL'
        assert engine.position == 0 # Should be closed

    def test_zero_price_handling(self, engine, sample_data):
        # Set a price to 0 to test division by zero protection if any
        sample_data.loc[sample_data.index[2], 'open'] = 0
        
        signals = pd.Series(0, index=sample_data.index)
        signals.iloc[1] = 1
        
        # Should not crash, but might not trade or handle gracefully
        try:
            engine.run(sample_data, signals)
        except ZeroDivisionError:
            pytest.fail("Engine raised ZeroDivisionError on zero price")
        except Exception as e:
            # Depending on implementation, it might raise ValueError or just skip
            pass

    def test_empty_data(self, engine):
        df = pd.DataFrame()
        signals = pd.Series(dtype=float)
        
        # Should handle empty data gracefully
        engine.run(df, signals)
        assert len(engine.trades) == 0
        assert len(engine.equity_curve) == 0

    def test_bankruptcy_check(self, engine, sample_data):
        # Simulate massive loss
        engine.current_capital = 1.0 # Near zero
        
        signals = pd.Series(0, index=sample_data.index)
        signals.iloc[1] = 1
        
        engine.run(sample_data, signals)
        # Should verify behavior (e.g. no trade or stop)
