import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    # Base Directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = DATA_DIR / "market_data.db"
    VERSION: str = "1.0.0"

    # AI Configuration
    API_KEY: str = os.getenv("API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o")
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_TOP_P: float = 0.9

    # Trading Constants
    INITIAL_CAPITAL: float = 10000.0
    COMMISSION_RATE: float = 0.001  # 0.1%
    SLIPPAGE: float = 0.0005        # 5 bps
    MIN_COMMISSION: float = 1.0     # $1 minimum
    EPSILON: float = 1e-9
    RISK_FREE_RATE: float = 0.02    # 2% Annual
    DEFAULT_START_DATE: str = "2000-01-01"

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    # Base Directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = DATA_DIR / "market_data.db"
    VERSION: str = "1.0.0"

    # AI Configuration
    API_KEY: str = os.getenv("API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o")
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_TOP_P: float = 0.9

    # Trading Constants
    INITIAL_CAPITAL: float = 10000.0
    COMMISSION_RATE: float = 0.001  # 0.1%
    SLIPPAGE: float = 0.0005        # 5 bps
    MIN_COMMISSION: float = 1.0     # $1 minimum
    EPSILON: float = 1e-9
    RISK_FREE_RATE: float = 0.02    # 2% Annual
    DEFAULT_START_DATE: str = "2000-01-01"

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    # Base Directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = DATA_DIR / "market_data.db"
    VERSION: str = "1.0.0"

    # AI Configuration
    API_KEY: str = os.getenv("API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o")
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_TOP_P: float = 0.9

    # Trading Constants
    INITIAL_CAPITAL: float = 10000.0
    COMMISSION_RATE: float = 0.001  # 0.1%
    SLIPPAGE: float = 0.0005        # 5 bps
    MIN_COMMISSION: float = 1.0     # $1 minimum
    EPSILON: float = 1e-9
    RISK_FREE_RATE: float = 0.02    # 2% Annual
    DEFAULT_START_DATE: str = "2000-01-01"

    # Strategy Constants
    DEFAULT_MA_WINDOW: int = 20
    DEFAULT_RSI_PERIOD: int = 14
    DEFAULT_RSI_BUY_THRESHOLD: int = 30
    DEFAULT_RSI_SELL_THRESHOLD: int = 70

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    ) # Ignore extra env vars

# Singleton instance
settings = Settings()

# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
