import pytest
import os
import json
from src.strategies.manager import StrategyManager

# Use a temporary file for testing
TEST_STRATEGY_FILE = "tests/test_user_strategies.json"

@pytest.fixture
def manager():
    # Setup: Create a manager instance with a test file
    if os.path.exists(TEST_STRATEGY_FILE):
        os.remove(TEST_STRATEGY_FILE)
    
    mgr = StrategyManager(filepath=TEST_STRATEGY_FILE)
    yield mgr
    
    # Teardown: Remove the test file
    if os.path.exists(TEST_STRATEGY_FILE):
        os.remove(TEST_STRATEGY_FILE)

def test_save_strategy(manager):
    name = "TestStrategy"
    code = "print('Hello World')"
    manager.save(name, code)
    
    assert os.path.exists(TEST_STRATEGY_FILE)
    with open(TEST_STRATEGY_FILE, 'r') as f:
        data = json.load(f)
    assert name in data
    assert data[name] == code

def test_get_strategy(manager):
    name = "TestStrategy"
    code = "print('Hello World')"
    manager.save(name, code)
    
    retrieved_code = manager.get(name)
    assert retrieved_code == code

def test_get_non_existent_strategy(manager):
    assert manager.get("NonExistent") is None

def test_delete_strategy(manager):
    name = "TestStrategy"
    code = "print('Hello World')"
    manager.save(name, code)
    
    manager.delete(name)
    assert manager.get(name) is None
    
    with open(TEST_STRATEGY_FILE, 'r') as f:
        data = json.load(f)
    assert name not in data

def test_duplicate_name_check(manager):
    name = "TestStrategy"
    code1 = "print('Version 1')"
    code2 = "print('Version 2')"
    
    manager.save(name, code1)
    assert manager.get(name) == code1
    
    # Should overwrite
    manager.save(name, code2)
    assert manager.get(name) == code2

def test_list_all(manager):
    manager.save("Strat1", "code1")
    manager.save("Strat2", "code2")
    
    strategies = manager.list_all()
    assert "Strat1" in strategies
    assert "Strat2" in strategies
    assert len(strategies) == 2
