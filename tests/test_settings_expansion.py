import pytest
from src.config.settings import settings

def test_settings_expansion_existence():
    """
    Case A: Verify new constants existence
    """
    assert hasattr(settings, "KNOWN_CRYPTOS"), "KNOWN_CRYPTOS missing from settings"
    assert hasattr(settings, "MIN_EXPOSURE_THRESHOLD"), "MIN_EXPOSURE_THRESHOLD missing from settings"
    assert hasattr(settings, "MAX_CHUNK_YEARS"), "MAX_CHUNK_YEARS missing from settings"
    assert hasattr(settings, "DEFAULT_TIMEOUT"), "DEFAULT_TIMEOUT missing from settings"

def test_settings_expansion_values():
    """
    Case B: Verify default values
    """
    # KNOWN_CRYPTOS
    assert isinstance(settings.KNOWN_CRYPTOS, (set, list)), "KNOWN_CRYPTOS should be a set or list"
    expected_cryptos = {'BTC', 'ETH', 'DOGE', 'XRP', 'SOL', 'ADA'}
    # Check if expected cryptos are present. 
    # Note: The user asked for these specific ones, so we check they are in the set.
    # We convert to set for comparison if it's a list.
    current_cryptos = set(settings.KNOWN_CRYPTOS)
    assert expected_cryptos.issubset(current_cryptos), f"Missing cryptos. Expected at least {expected_cryptos}, got {current_cryptos}"

    # MIN_EXPOSURE_THRESHOLD
    assert isinstance(settings.MIN_EXPOSURE_THRESHOLD, float), "MIN_EXPOSURE_THRESHOLD should be a float"
    assert settings.MIN_EXPOSURE_THRESHOLD == 0.001, "MIN_EXPOSURE_THRESHOLD should be 0.001"

    # MAX_CHUNK_YEARS
    assert isinstance(settings.MAX_CHUNK_YEARS, int), "MAX_CHUNK_YEARS should be an int"
    assert settings.MAX_CHUNK_YEARS == 5, "MAX_CHUNK_YEARS should be 5"

    # DEFAULT_TIMEOUT
    assert isinstance(settings.DEFAULT_TIMEOUT, float), "DEFAULT_TIMEOUT should be a float"
    assert settings.DEFAULT_TIMEOUT == 30.0, "DEFAULT_TIMEOUT should be 30.0"
