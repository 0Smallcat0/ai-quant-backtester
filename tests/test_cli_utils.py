import pytest
from unittest.mock import MagicMock, patch
import argparse
from src.utils import strip_quotes, sanitize_ticker

def test_strip_quotes():
    """
    Case A: Verify Utils (strip_quotes)
    """
    # Test single quotes
    assert strip_quotes("'2023-01-01'") == "2023-01-01"
    # Test double quotes
    assert strip_quotes('"My Strategy"') == "My Strategy"
    # Test mixed/nested (should strip outer)
    assert strip_quotes("'\"Nested\"'") == "Nested"
    # Test no quotes
    assert strip_quotes("Normal Text") == "Normal Text"
    # Test empty
    assert strip_quotes("") == ""
    # Test None (if handled, though type hint says str. Utils usually handle None gracefully or fail. 
    # The requirement says "if not text: return ''")
    assert strip_quotes(None) == ""

def test_cli_integration_logic():
    """
    Case B: Verify CLI Integration logic simulation.
    We simulate the logic that will be in run_backtest.py
    """
    # Simulate args
    args = MagicMock()
    args.ticker = "' aApl '"
    args.start = "'2023-01-01'"
    args.strategy_name = '"MyStrategy"'
    
    # Apply logic intended for run_backtest.py
    # Ticker uses sanitize_ticker
    cleaned_ticker = sanitize_ticker(args.ticker)
    # Start uses strip_quotes
    cleaned_start = strip_quotes(args.start)
    # Strategy uses strip_quotes
    cleaned_strategy = strip_quotes(args.strategy_name)
    
    assert cleaned_ticker == "AAPL"
    assert cleaned_start == "2023-01-01"
    assert cleaned_strategy == "MyStrategy"
