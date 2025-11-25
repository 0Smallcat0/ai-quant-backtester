import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Database
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "market_data.db"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# AI Configuration (loaded from .env)
API_KEY = os.getenv("API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME") or "gpt-4o"

# Trading Constants
INITIAL_CAPITAL = 100000.0
COMMISSION_RATE = 0.001  # 0.1%
SLIPPAGE = 0.0005        # 5 bps
MIN_COMMISSION = 1.0     # $1 minimum
EPSILON = 1e-9

# Strategy Constants
DEFAULT_MA_WINDOW = 20
DEFAULT_RSI_PERIOD = 14
DEFAULT_RSI_BUY_THRESHOLD = 30
DEFAULT_RSI_SELL_THRESHOLD = 70