import sys
import os
import logging
from pathlib import Path
from src.config.settings import settings

def setup_logging(name: str = __name__) -> logging.Logger:
    """
    Configure and return a logger instance with standardized settings.
    """
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=settings.LOG_FORMAT
    )
    return logging.getLogger(name)

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

def categorize_ticker(ticker: str) -> str:
    """
    Categorize ticker symbol into:
    - Crypto: Ends with -USD
    - TW: Ends with .TW or .TWO
    - US: Alpha only (e.g. AAPL)
    - Other: Everything else
    """
    if not ticker:
        return "Other"
        
    ticker = ticker.upper().strip()
    
    if ticker.endswith("-USD"):
        return "Crypto"
    if ticker.endswith(".TW") or ticker.endswith(".TWO"):
        return "TW"
    if ticker.isalpha():
        return "US"
        
    return "Other"
