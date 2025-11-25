from pathlib import Path

# Single Source of Truth for Configuration Parameters

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "market_data.db"

# Default Trading Parameters
DEFAULT_INITIAL_CAPITAL = 10000.0
DEFAULT_COMMISSION = 0.001  # 0.1%
DEFAULT_SLIPPAGE = 0.0005   # 0.05%
DEFAULT_MIN_COMMISSION = 0.0

# Default Strategy Parameters
DEFAULT_MA_WINDOW = 20
DEFAULT_RSI_PERIOD = 14
DEFAULT_RSI_BUY_THRESHOLD = 30
DEFAULT_RSI_SELL_THRESHOLD = 70

# System Constants
EPSILON = 1e-9
VERSION = "v1.1.0"
