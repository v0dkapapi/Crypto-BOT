import logging
import os
from typing import Dict, List, Optional
import requests
from datetime import datetime, timedelta
from textblob import TextBlob
import pandas as pd

from config.config import config
from services.data_service import crypto_data_service
from services.db_service import db_service
from services.llm_service import llm_service

logger = logging.getLogger(__name__)

class CryptoAnalysisService:
    def __init__(self):
        self.api_key = config.api.news_api_key
        self.session = requests.Session()
        
        # Create news data directory if it doesn't exist
        self.news_dir = os.path.join(os.getcwd(), 'data', 'news')
        os.makedirs(self.news_dir, exist_ok=True)

    def _get_news_file_path(self, symbol: str) -> str:
        """Get the path for a news cache file"""
        return os.path.join(self.news_dir, f"{symbol}_news.csv")

    def _should_update_news(self, symbol: str, update_interval_minutes: int = 60) -> bool:
        """Check if news should be updated based on MongoDB timestamp"""
        latest_news = db_service.get_latest_news(symbol)
        if not latest_news:
            return True
            
        last_update = latest_news.get('timestamp')
        if not last_update:
            return True
            
        last_update = pd.to_datetime(last_update)
        elapsed_time = datetime.now() - last_update
        return elapsed_time.total_seconds() > (update_interval_minutes * 60)

    def _calculate_overall_sentiment(self, news_items: List[Dict]) -> str:
        """Calculate overall sentiment from news items"""
        if not news_items:
            return "Neutral"
            
        try:
            # Calculate average sentiment
            total_sentiment = sum(item['sentiment'] for item in news_items)
            avg_sentiment = total_sentiment / len(news_items)
            
            # Classify sentiment
            if avg_sentiment > 0.2:
                return "Positive"
            elif avg_sentiment < -0.2:
                return "Negative"
            else:
                return "Neutral"
                
        except Exception as e:
            logger.error(f"Error calculating sentiment: {str(e)}")
            return "Neutral"

    def get_crypto_news(self, symbol: str = 'BTC', limit: int = 10, force_update: bool = False) -> List[Dict]:
        """Fetch crypto news using Alpha Vantage News API with caching"""
        try:
            # Check if we need to update news
            if not force_update and not self._should_update_news(symbol):
                logger.info(f"Loading cached news for {symbol}")
                cached_news = db_service.get_latest_news(symbol)
                if cached_news and 'news_items' in cached_news:
                    return cached_news['news_items']

            # If update needed or forced, fetch new data
            params = {
                'function': 'NEWS_SENTIMENT',
                'tickers': f'CRYPTO:{symbol}',
                'apikey': config.api.alpha_vantage_key,
                'limit': limit
            }
            
            response = self.session.get(config.api.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if 'feed' not in data:
                return []
                
            news_items = []
            for item in data['feed']:
                # Calculate sentiment using TextBlob
                sentiment = TextBlob(item['title'] + " " + item['summary']).sentiment.polarity
                
                news_item = {
                    'title': item['title'],
                    'summary': item['summary'],
                    'url': item['url'],
                    'source': item['source'],
                    'timestamp': item['time_published'],
                    'sentiment': sentiment,
                    'sentiment_label': 'Positive' if sentiment > 0 else 'Negative' if sentiment < 0 else 'Neutral'
                }
                news_items.append(news_item)
            
            # Save to MongoDB
            news_data = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'news_items': news_items
            }
            db_service.save_news_data(symbol, news_data)
            
            # Save to CSV as backup
            news_df = pd.DataFrame(news_items)
            news_file_path = self._get_news_file_path(symbol)
            news_df.to_csv(news_file_path, index=False)
            
            return news_items
            
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {str(e)}")
            # Try to load from cache if API fails
            try:
                cached_news = db_service.get_latest_news(symbol)
                if cached_news and 'news_items' in cached_news:
                    return cached_news['news_items']
                    
                # If MongoDB fails, try CSV backup
                news_file_path = self._get_news_file_path(symbol)
                if os.path.exists(news_file_path):
                    news_df = pd.read_csv(news_file_path)
                    return news_df.to_dict('records')
                    
            except Exception as cache_error:
                logger.error(f"Error loading cached news: {str(cache_error)}")
            return []

    def generate_market_analysis(self, symbol: str = 'BTC') -> Dict:
        """Generate comprehensive market analysis using LLM"""
        try:
            # Get market data
            market_data = crypto_data_service.get_market_summary(symbol)
            news = self.get_crypto_news(symbol)
            
            if not market_data:
                return {}
            
            # Get LLM analysis
            llm_analysis = llm_service.generate_analysis(market_data, news)
            
            # Combine with regular analysis
            analysis = {
                'timestamp': datetime.now().isoformat(),
                'price_analysis': {
                    'current_price': market_data.get('price', 0),
                    'price_change_24h': market_data.get('price_change_24h', 0),
                    'trend': market_data.get('ma_signal', 'neutral'),
                },
                'technical_indicators': {
                    'rsi_condition': 'Overbought' if market_data.get('rsi', 0) > 70 else 'Oversold' if market_data.get('rsi', 0) < 30 else 'Neutral',
                    'macd_signal': market_data.get('macd_signal', 'neutral'),
                },
                'market_sentiment': {
                    'news_sentiment': self._calculate_overall_sentiment(news),
                    'news_count': len(news),
                    'latest_news': news[:3] if news else []
                },
                'llm_analysis': llm_analysis
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error generating analysis for {symbol}: {str(e)}")
            return {}

# Create global instance
analysis_service = CryptoAnalysisService()