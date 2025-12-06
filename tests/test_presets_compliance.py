import pytest
import pandas as pd
import numpy as np
from src.strategies.presets import PRESET_STRATEGIES
from src.strategies.base import Strategy

class TestPresetsCompliance:
    
    @pytest.fixture
    def sample_data(self):
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        data = pd.DataFrame({
            'open': np.random.rand(100) * 100,
            'high': np.random.rand(100) * 100,
            'low': np.random.rand(100) * 100,
            'close': np.random.rand(100) * 100,
            'volume': np.random.randint(100, 1000, 100)
        }, index=dates)
        return data

    def test_presets_structure(self):
        """Case A: Presets Safety - Check inheritance and generate_signals existence."""
        for name, strategy_cls in PRESET_STRATEGIES.items():
            # Check inheritance
            assert issubclass(strategy_cls, Strategy), f"{name} must inherit from Strategy"
            
            # Check instantiation
            strategy = strategy_cls()
            assert hasattr(strategy, 'generate_signals'), f"{name} must have generate_signals method"

    def test_safe_rolling_usage(self, sample_data):
        """Case B: Data Integrity - Check if safe_rolling is used (indirectly via behavior or mocking)."""
        # We can check if the strategy uses safe_rolling by inspecting the code or behavior.
        # Since we are refactoring to use safe_rolling, we expect the logic to rely on shifted data.
        # However, checking exact implementation details via test might be brittle.
        # Instead, let's check if the output signal at T depends on Close at T (Look-ahead bias).
        
        # For MovingAverageStrategy: Signal at T should depend on MA calculated from T-1 backwards.
        # If we change Close at T, Signal at T should NOT change if it's purely based on T-1 indicators.
        # BUT, the strategy logic is: Buy when Close > MA.
        # MA is the indicator. If MA uses safe_rolling, MA at T is based on [T-window, T-1].
        # The comparison is Close(T) > MA(T). So Signal(T) DOES depend on Close(T).
        # Wait, the requirement says: "Logic: Replace all rolling().mean() with self.safe_rolling(..., 'mean')".
        # safe_rolling shifts by 1. So MA(T) = Mean(Close[T-window...T-1]).
        # Comparison: Close(T) > MA(T).
        # This is valid (comparing current price to previous average).
        
        from src.strategies.presets import MovingAverageStrategy
        
        strategy = MovingAverageStrategy(window=10)
        
        # We want to verify that MA column is shifted.
        # We can inspect the internal dataframe if we modify the strategy to expose it, 
        # or we can just check the 'ma' column in the returned df if it exists.
        
        # Let's run generate_signals
        df_out = strategy.generate_signals(sample_data)
        
        # Check if 'ma' column exists (it usually does in the implementation)
        if 'ma' in df_out.columns:
            # Manually calculate safe MA
            expected_ma = sample_data['close'].shift(1).rolling(window=10).mean()
            pd.testing.assert_series_equal(df_out['ma'], expected_ma, check_names=False, obj="Moving Average (Safe)")
            
    def test_bollinger_safe_rolling(self, sample_data):
        from src.strategies.presets import BollingerBreakoutStrategy
        strategy = BollingerBreakoutStrategy(window=20)
        df_out = strategy.generate_signals(sample_data)
        
        if 'upper' in df_out.columns:
            # Verify calculation uses shifted data
            shifted_close = sample_data['close'].shift(1)
            expected_ma = shifted_close.rolling(window=20).mean()
            expected_std = shifted_close.rolling(window=20).std()
            expected_upper = expected_ma + (expected_std * 2.0)
            
            pd.testing.assert_series_equal(df_out['upper'], expected_upper, check_names=False, obj="Bollinger Upper Band (Safe)")

