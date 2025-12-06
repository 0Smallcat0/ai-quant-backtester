import logging
import sys
from src.config.settings import settings

def setup_logging(name: str) -> logging.Logger:
    """
    Setup logging with consistent format and handlers.
    """
    logger = logging.getLogger(name)
    
    # Prevent adding multiple handlers if already configured
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(settings.LOG_LEVEL)
    
    formatter = logging.Formatter(settings.LOG_FORMAT)
    
    # Create console handler with formatting
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(settings.LOG_FORMAT))
    logger.addHandler(handler)
    
    return logger
