import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
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

    # Sentiment Configuration
    SENTIMENT_MODEL_TYPE: str = "local_hybrid"  # or "simple_remote"
    FINBERT_PATH: str = "yiyanghkust/finbert-tone"
    ABSA_MODEL_PATH: str = "snrspeaks/Gemma-2B-it-Finance-Aspect-Based-Sentiment-Analyzer"
    SENTIMENT_FILTER_THRESHOLD: float = 0.6

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

    # Data Engine Settings
    KNOWN_CRYPTOS: set = {'BTC', 'ETH', 'DOGE', 'XRP', 'SOL', 'ADA'}
    MAX_CHUNK_YEARS: int = 5
    DEFAULT_TIMEOUT: float = 30.0
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 2.0
    RATE_LIMIT_SLEEP: float = 0.5
    
    # ----------------------------------------------------------------
    # Data Integrity & Update Strategy
    # ----------------------------------------------------------------
    # "INCREMENTAL": (Default) Skip existing dates, append new data only. Fast.
    # "FULL_VERIFY": Download full history, compare with DB. 
    #                If conflict > tolerance, trigger backup provider voting.
    DATA_UPDATE_MODE: str = "INCREMENTAL" 
    
    # Tolerance for floating point comparison between data sources
    DATA_DIFF_TOLERANCE: float = 1e-4
    MARKET_CONFIG: dict = {
        'TW': {'suffixes': ['.TW', '.TWO'], 'pattern': r"^\d{4,6}[a-zA-Z]?$", 'default_on_fail': True},
        'CRYPTO': {'suffixes': ['-USD'], 'pattern': r"^[A-Z]+$", 'known': {'BTC', 'ETH', 'DOGE', 'XRP', 'SOL', 'ADA'}, 'default_on_fail': False},
        'US': {'suffixes': [], 'pattern': r"^[A-Z]+$", 'default_on_fail': False}
    }

    # News Engine Settings
    NEWS_BASE_URLS: dict = {
        'TW': "https://news.google.com/rss/search?q={ENCODED_QUERY}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
        'US': "https://news.google.com/rss/search?q={ENCODED_QUERY}&hl=en-US&gl=US&ceid=US:en",
        'CRYPTO': "https://news.google.com/rss/search?q={ENCODED_QUERY}&hl=en-US&gl=US&ceid=US:en"
    }
    NEWS_SOURCES: dict = {
        'TW': ["site:cnyes.com", "site:udn.com", "site:bnext.com.tw", "site:moneydj.com", "site:tw.stock.yahoo.com", "site:ctee.com.tw", "site:finance.ettoday.net", "site:anue.com"],
        'US': ["site:reuters.com", "site:cnbc.com", "site:bloomberg.com", "site:finance.yahoo.com", "site:marketwatch.com", "site:investing.com", "site:barrons.com", "site:thestreet.com", "site:fool.com", "site:forbes.com", "site:businessinsider.com", "site:seekingalpha.com", "site:benzinga.com", "site:tipranks.com"],
        'CRYPTO': ["site:coindesk.com", "site:cointelegraph.com", "site:theblock.co", "site:decrypt.co", "site:blockworks.co", "site:cryptoslate.com", "site:bitcoinmagazine.com", "site:u.today"]
    }
    NEWS_TOP_N_LIMIT: int = 10
    LLM_MAX_INPUT_CHARS: int = 6000 # Approx 1500-2000 tokens
    SENTIMENT_DECAY_HALFLIFE: float = 5.0
    SENTIMENT_NOISE_THRESHOLD: float = 0.01
    
    # News Engine - Noise Filtering
    NEWS_NOISE_KEYWORDS: list = ["速報", "買超", "賣超", "排行榜", "熱門股", "盤前", "盤後", "漲跌停", "統整"]
    
    # News Engine - Impact Ranking
    NEWS_IMPACT_SCORES: dict = {
        'TIER_1': 10.0,
        'TIER_2': 5.0,
        'SOURCE_BONUS': 3.0,
        'BASE_SCORE': 1.0
    }
    
    NEWS_IMPACT_KEYWORDS: dict = {
        'TW': {
            'TIER_1': ["財報", "營收", "EPS", "股利", "配息", "法說", "併購", "收購", "違約", "裁員", "擴廠", "資本支出"],
            'TIER_2': ["漲停", "跌停", "創新高", "創新低", "大漲", "崩跌", "主力", "外資"]
        },
        'US': {
            'TIER_1': ["earnings", "revenue", "eps", "dividend", "acquisition", "merger", "default", "layoff", "expansion", "guidance", "sec", "fed"],
            'TIER_2': ["surge", "plunge", "all-time high", "crash", "breakout", "upgrade", "downgrade"]
        }
    }
    
    NEWS_PREMIUM_SOURCES: list = ["reuters", "bloomberg", "wsj", "coindesk"]
    
    # News Engine - Timezone & Rollover
    MARKET_TIMEZONES: dict = {
        'TW': 'Asia/Taipei',
        'US': 'US/Eastern',
        'CRYPTO': 'UTC'
    }
    
    MARKET_ROLLOVER_HOURS: dict = {
        'TW': 14,
        'US': 16,
        'CRYPTO': 24 # No rollover
    }

    # Strategy Configuration
    USER_STRATEGIES_PATH: Path = DATA_DIR / "user_strategies.json"
    FORBIDDEN_REGEXES: list = [
        r"\.shift\s*\(\s*-",      # Matches .shift(-1), .shift( -1 ), etc.
        r"shift\s*\(\s*-",        # Variant without dot
        r"\.iloc\s*\[\s*i\s*\+\s*\d+",  # Matches .iloc[i+1], .iloc[ i + 1 ], etc.
        r"\.iloc\s*\[\s*:\s*-?\d+",  # .iloc[:-5] Slicing lookahead
        r"\.iloc\s*\[\s*i\s*\+\s*\d+", # .iloc[i+1] Future index
        r"\.iloc\s*\[\s*\d+\s*:"     # .iloc[10:] Future slice
    ]

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(levelname)s - %(message)s"

    # Backtest Engine Settings
    MIN_EXPOSURE_THRESHOLD: float = 0.001  # 0.1% of Equity

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    ) # Ignore extra env vars
    
    @field_validator('NEWS_TOP_N_LIMIT')
    @classmethod
    def validate_top_n(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("NEWS_TOP_N_LIMIT must be positive")
        return v

    @field_validator('SENTIMENT_DECAY_HALFLIFE')
    @classmethod
    def validate_halflife(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("SENTIMENT_DECAY_HALFLIFE must be positive")
        return v

# Singleton instance
settings = Settings()

# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
