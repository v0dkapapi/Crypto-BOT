import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Dict, List

# Load environment variables
load_dotenv()

@dataclass
class APIConfig:
    """API Configuration settings"""
    alpha_vantage_key: str = os.getenv('ALPHA_VANTAGE_API_KEY', '')
    news_api_key: str = os.getenv('NEWS_API_KEY', '')
    base_url: str = "https://www.alphavantage.co/query"
    
@dataclass
class DatabaseConfig:
    """Database Configuration settings"""
    data_dir: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
    raw_dir: str = os.path.join(data_dir, 'raw')
    processed_dir: str = os.path.join(data_dir, 'processed')

@dataclass
class CryptoConfig:
    """Cryptocurrency Configuration settings"""
    default_symbols: List[str] = ('BTC', 'ETH', 'BNB', 'XRP', 'ADA')
    update_interval: int = 60  # seconds
    historical_days: int = 365
    technical_indicators: List[str] = ('RSI', 'MACD', 'EMA')

@dataclass
class AppConfig:
    """Main Application Configuration"""
    api: APIConfig = APIConfig()
    db: DatabaseConfig = DatabaseConfig()
    crypto: CryptoConfig = CryptoConfig()
    debug: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    log_dir: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')

    def __post_init__(self):
        """Create necessary directories if they don't exist"""
        os.makedirs(self.db.raw_dir, exist_ok=True)
        os.makedirs(self.db.processed_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)

# Create global config instance
config = AppConfig()

# Validation function for API keys
def validate_api_keys() -> Dict[str, bool]:
    """Validate that all required API keys are present"""
    return {
        'alpha_vantage': bool(config.api.alpha_vantage_key),
        'news_api': bool(config.api.news_api_key)
    }

# Technical Analysis Parameters
TECHNICAL_PARAMS = {
    'RSI': {
        'timeperiod': 14,
        'overbought': 70,
        'oversold': 30
    },
    'MACD': {
        'fastperiod': 12,
        'slowperiod': 26,
        'signalperiod': 9
    },
    'EMA': {
        'timeperiods': [20, 50, 200]
    }
}

# Chart Configuration
CHART_CONFIG = {
    'default_height': 600,
    'default_width': 800,
    'theme': 'streamlit',
    'color_scheme': {
        'primary': '#2962FF',
        'secondary': '#FF6B6B',
        'positive': '#00C853',
        'negative': '#FF5252',
        'neutral': '#757575'
    }
}

# News Configuration
NEWS_CONFIG = {
    'update_interval': 300,  # 5 minutes
    'max_articles': 50,
    'relevance_threshold': 0.6
}

# Logging Configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(config.log_dir, 'app.log'),
            'formatter': 'standard'
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        }
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if config.debug else 'INFO',
            'propagate': True
        }
    }
}