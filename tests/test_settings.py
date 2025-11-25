import pytest
import os
from src.config.settings import Settings

class TestSettings:
    def test_defaults(self):
        """Verify default values match the requirements."""
        settings = Settings()
        assert settings.INITIAL_CAPITAL == 10000.0
        assert settings.COMMISSION_RATE == 0.001
        assert settings.SLIPPAGE == 0.0005
        assert settings.MIN_COMMISSION == 1.0
        assert settings.RISK_FREE_RATE == 0.02

    def test_env_override(self):
        """Verify environment variables override defaults."""
        os.environ["INITIAL_CAPITAL"] = "50000.0"
        os.environ["RISK_FREE_RATE"] = "0.05"
        
        try:
            # Reload settings (Pydantic reads env vars on instantiation)
            settings = Settings()
            assert settings.INITIAL_CAPITAL == 50000.0
            assert settings.RISK_FREE_RATE == 0.05
        finally:
            # Cleanup
            del os.environ["INITIAL_CAPITAL"]
            del os.environ["RISK_FREE_RATE"]

    def test_type_validation(self):
        """Verify type checking works."""
        os.environ["INITIAL_CAPITAL"] = "invalid_float"
        
        try:
            with pytest.raises(ValueError):
                Settings()
        finally:
            del os.environ["INITIAL_CAPITAL"]
