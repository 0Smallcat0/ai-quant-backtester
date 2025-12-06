import sys
import os
import logging
from pathlib import Path
from src.config.settings import settings



def sanitize_ticker(ticker: str) -> str:
    """
    Standardize ticker format:
    - Remove leading/trailing whitespace
    - Remove single/double quotes
    - Convert to uppercase
    """
    if not ticker:
        return ""
    return ticker.strip().strip("'").strip('"').strip().upper()

def strip_quotes(text: str) -> str:
    """Remove single and double quotes from a string without changing case."""
    if not text:
        return ""
    return text.strip().strip("'").strip('"')

def add_project_root() -> None:
    """
    Add the project root directory to sys.path to allow absolute imports.
    Assumes this file is located in src/utils.py or similar depth.
    """
    # Get the directory containing this file (src/)
    current_file = Path(__file__).resolve()
    src_dir = current_file.parent
    
    # Get project root (parent of src/)
    project_root = src_dir.parent
    
    # Add project root to sys.path if not present
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        
    # Also ensure src/ is in sys.path for convenience (optional but helpful for some imports)
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

def detect_market(ticker: str) -> str:
    """
    Detect market type for a given ticker using settings.MARKET_CONFIG.
    Returns: 'TW', 'CRYPTO', 'US', or 'Other'
    """
    if not ticker:
        return "Other"
        
    ticker = ticker.upper().strip()
    
    # 1. Check suffixes/patterns from config
    # We iterate through config to find a match
    # MARKET_CONFIG is { 'TW': ..., 'CRYPTO': ..., 'US': ... }
    
    # Priority: Suffix match > Pattern match (if safe)
    
    for market, config in settings.MARKET_CONFIG.items():
        # Check Known set first (for Crypto mostly)
        known = config.get('known', set())
        if ticker in known:
            return market

        suffixes = config.get('suffixes', [])
        for suffix in suffixes:
            if ticker.endswith(suffix):
                return market
                
    # If no suffix match, check patterns
    import re
    for market, config in settings.MARKET_CONFIG.items():
        pattern = config.get('pattern')
        if pattern and re.match(pattern, ticker):
            # Special handling for default implicit markets (US vs Crypto)
            # US pattern matches all alphas, Crypto also matches all alphas
            # We usually rely on suffix or 'known' for Crypto.
            
            # If it's CRYPTO but not in known and no suffix, we might want to skip 
            # effectively treating it as US if pattern overlaps
            if market == 'CRYPTO':
                # Crypto usually requires explicit -USD or being in 'known'
                continue
                
            return market
            
    return "Other"


