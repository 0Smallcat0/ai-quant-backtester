import logging
import logging.handlers
import queue
import sys
import atexit
from src.config.settings import settings

# [PERFORMANCE] Global Log Queue and Listener
# We use a global listener to ensure only one thread handles I/O
_log_queue = queue.Queue(-1)
_queue_handler = logging.handlers.QueueHandler(_log_queue)
_console_handler = logging.StreamHandler(sys.stderr)
_console_handler.setFormatter(logging.Formatter(settings.LOG_FORMAT))

# QueueListener runs in a separate internal thread
_listener = logging.handlers.QueueListener(_log_queue, _console_handler)
_listener.start()

# Ensure listener stops on exit
atexit.register(_listener.stop)

def setup_logging(name: str) -> logging.Logger:
    """
    Setup logging with consistent format and handlers.
    Uses QueueHandler for non-blocking I/O.
    """
    logger = logging.getLogger(name)
    
    # Prevent adding multiple handlers if already configured
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(settings.LOG_LEVEL)
    
    # Add the asynchronous QueueHandler
    logger.addHandler(_queue_handler)
    
    # Do not add StreamHandler directly to logger to avoid double printing/blocking
    # The listener handles the actual output.
    
    return logger

class TornadoNoiseFilter(logging.Filter):
    """
    Filter to suppress benign Tornado/WebSocket errors caused by client disconnects.
    """
    def filter(self, record):
        msg = record.getMessage()
        
        # Filter by message content
        if "Stream is closed" in msg or "WebSocketClosedError" in msg:
            return False
            
        # Filter by exception type if present
        if record.exc_info:
            exc_type, _, _ = record.exc_info
            if exc_type and ("StreamClosedError" in str(exc_type) or "WebSocketClosedError" in str(exc_type)):
                return False
                
        return True

# Apply filter to the main console handler
_console_handler.addFilter(TornadoNoiseFilter())

# Also proactively apply to noisy third-party loggers
for logger_name in ["tornado.application", "tornado.access", "tornado.general", "asyncio"]:
    logging.getLogger(logger_name).addFilter(TornadoNoiseFilter())
