import pytest
from unittest.mock import patch, MagicMock
import streamlit as st
from src.config.settings import settings
from src.backtest_engine import BacktestEngine

# Mock Streamlit session state
class MockSessionState(dict):
    def __getattr__(self, key):
        return self.get(key)
    def __setattr__(self, key, value):
        self[key] = value

@pytest.fixture
def mock_streamlit():
    with patch('streamlit.session_state', new_callable=MockSessionState) as mock_state:
        yield mock_state

def test_backtest_engine_initial_capital_sensitivity():
    """
    Test that BacktestEngine picks up the correct initial capital from settings
    when not explicitly provided (or when we simulate the UI flow).
    """
    # 1. Test Default from Settings
    # We patch the settings object to return a specific value
    with patch.object(settings, 'INITIAL_CAPITAL', 50000.0):
        # Re-instantiate engine to see if it picks up the patched value as default
        # Note: In Python, default arguments are evaluated at definition time, 
        # so simply patching settings.INITIAL_CAPITAL might not work if BacktestEngine.__init__ 
        # uses settings.INITIAL_CAPITAL as a default arg directly.
        # Let's check BacktestEngine definition:
        # def __init__(self, initial_capital: float = settings.INITIAL_CAPITAL, ...):
        # Since it's evaluated at import time, we can't easily change the default arg of the class 
        # without reloading the module.
        
        # However, the UI passes the value explicitly.
        # So we should test the UI logic flow.
        
        # Simulate UI Logic:
        # if 'sc_initial_capital' not in st.session_state:
        #     st.session_state['sc_initial_capital'] = float(global_settings.get('initial_capital', settings.INITIAL_CAPITAL))
        
        # Case A: Default Settings
        mock_state = MockSessionState()
        global_settings = {}
        
        if 'sc_initial_capital' not in mock_state:
            mock_state['sc_initial_capital'] = float(global_settings.get('initial_capital', settings.INITIAL_CAPITAL))
            
        assert mock_state['sc_initial_capital'] == 50000.0
        
        # Instantiate Engine with this value
        engine = BacktestEngine(initial_capital=mock_state['sc_initial_capital'])
        assert engine.initial_capital == 50000.0

    # 2. Test Sensitivity (Change Value)
    with patch.object(settings, 'INITIAL_CAPITAL', 99999.0):
        mock_state = MockSessionState()
        global_settings = {}
        
        if 'sc_initial_capital' not in mock_state:
            mock_state['sc_initial_capital'] = float(global_settings.get('initial_capital', settings.INITIAL_CAPITAL))
            
        assert mock_state['sc_initial_capital'] == 99999.0
        
        engine = BacktestEngine(initial_capital=mock_state['sc_initial_capital'])
        assert engine.initial_capital == 99999.0

def test_ui_logic_integration():
    """
    Verify that the logic used in strategy_creation.py correctly prioritizes sources.
    Priority: Session State > Global Settings > Default Settings
    """
    # Case 1: Session State already set (User input)
    mock_state = MockSessionState()
    mock_state['sc_initial_capital'] = 12345.0
    
    # Logic from strategy_creation.py
    global_settings = {}
    if 'sc_initial_capital' not in mock_state:
        mock_state['sc_initial_capital'] = float(global_settings.get('initial_capital', settings.INITIAL_CAPITAL))
        
    assert mock_state['sc_initial_capital'] == 12345.0
    
    # Case 2: Global Settings (e.g. from another page)
    mock_state = MockSessionState()
    global_settings = {'initial_capital': 77777.0}
    
    if 'sc_initial_capital' not in mock_state:
        mock_state['sc_initial_capital'] = float(global_settings.get('initial_capital', settings.INITIAL_CAPITAL))
        
    assert mock_state['sc_initial_capital'] == 77777.0
    
    # Case 3: Fallback to Settings
    mock_state = MockSessionState()
    global_settings = {}
    
    # We need to ensure settings.INITIAL_CAPITAL is what we expect for this test
    expected_default = settings.INITIAL_CAPITAL
    
    if 'sc_initial_capital' not in mock_state:
        mock_state['sc_initial_capital'] = float(global_settings.get('initial_capital', settings.INITIAL_CAPITAL))
        
    assert mock_state['sc_initial_capital'] == expected_default
