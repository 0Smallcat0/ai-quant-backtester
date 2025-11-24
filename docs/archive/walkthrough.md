# Strategy Security and Robustness Walkthrough

I have enhanced the security and robustness of the strategy management system. This includes improved lookahead detection, stricter input validation, and safer preset strategies.

## Changes

### 1. Enhanced Lookahead Detection
In `src/strategies/loader.py`, I added new regex patterns to detect:
- Slicing lookahead (e.g., `df.iloc[:-5]`)
- Future indexing (e.g., `df.iloc[i+1]`)
- Slicing from current to future (e.g., `df.iloc[10:]`)

```python
forbidden_regexes = [
    r"\.shift\s*\(\s*-",      
    r"shift\s*\(\s*-",        
    r"\.iloc\s*\[\s*i\s*\+\s*\d+",  
    r"\.iloc\s*\[\s*:\s*-?\d+",  # .iloc[:-5] Slicing lookahead
    r"shift\s*\(\s*-?\d+\s*\)",  # shift(-1)
    r"\.iloc\s*\[\s*i\s*\+\s*\d+", # .iloc[i+1] Future index
    r"\.iloc\s*\[\s*\d+\s*:"     # .iloc[10:] Future slice
]
```

### 2. Input Validation
In `src/strategies/manager.py`, I added guard clauses to `save_strategy` to prevent:
- Extremely long strategy names (>100 chars)
- Oversized strategy code (>1MB)

```python
if not name or len(name) > 100:
    raise ValueError("Strategy name must be 1-100 characters.")
if len(code) > 1_000_000: # 1MB limit
    raise ValueError("Strategy code exceeds size limit (1MB).")
```

### 3. Preset Robustness
In `src/strategies/presets.py`, I ensured that `generate_signals` explicitly fills NaNs with 0.0 before returning, preventing potential issues in the backtest engine.

```python
df['signal'] = df['signal'].fillna(0.0)
```

## Verification Results

### Automated Tests
I created `tests/test_strategy_safety.py` covering:
- **Case A**: Advanced Lookahead (Slicing, Shift)
- **Case B**: Input Validation
- **Case C**: Preset Robustness

All tests passed:
```
tests\test_strategy_safety.py ...                                        [ 42%]
tests\test_strategy_loader_fix.py ....                                   [100%]
============================== 7 passed in 0.63s ==============================
```
