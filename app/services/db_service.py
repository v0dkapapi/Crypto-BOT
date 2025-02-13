from typing import Dict, Optional, List
import logging
from datetime import datetime
import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

logger = logging.getLogger(__name__)

class MongoDBService:
    def __init__(self):
        self.client: MongoClient = MongoClient('mongodb://localhost:27017/')
        self.db: Database = self.client['crypto_assistant']
        self.historical_data: Collection = self.db['historical_data']
        self.processed_data: Collection = self.db['processed_data']
        self.news_data: Collection = self.db['news_data']
        
        # Create indexes
        self.historical_data.create_index([('symbol', pymongo.ASCENDING), ('timestamp', pymongo.ASCENDING)])
        self.processed_data.create_index([('symbol', pymongo.ASCENDING), ('timestamp', pymongo.ASCENDING)])
        self.news_data.create_index([('symbol', pymongo.ASCENDING), ('timestamp', pymongo.ASCENDING)])

    def save_historical_data(self, symbol: str, data: Dict) -> bool:
        """Save historical data to MongoDB"""
        try:
            data['symbol'] = symbol
            data['timestamp'] = datetime.now()
            self.historical_data.insert_one(data)
            return True
        except Exception as e:
            logger.error(f"Error saving historical data to MongoDB: {str(e)}")
            return False

    def save_processed_data(self, symbol: str, data: Dict) -> bool:
        """Save processed data to MongoDB"""
        try:
            data['symbol'] = symbol
            data['timestamp'] = datetime.now()
            self.processed_data.insert_one(data)
            return True
        except Exception as e:
            logger.error(f"Error saving processed data to MongoDB: {str(e)}")
            return False

    def get_latest_historical_data(self, symbol: str) -> Optional[Dict]:
        """Get the most recent historical data for a symbol"""
        try:
            data = self.historical_data.find_one(
                {'symbol': symbol},
                sort=[('timestamp', pymongo.DESCENDING)]
            )
            return data
        except Exception as e:
            logger.error(f"Error retrieving historical data from MongoDB: {str(e)}")
            return None

    def get_latest_processed_data(self, symbol: str) -> Optional[Dict]:
        """Get the most recent processed data for a symbol"""
        try:
            data = self.processed_data.find_one(
                {'symbol': symbol},
                sort=[('timestamp', pymongo.DESCENDING)]
            )
            return data
        except Exception as e:
            logger.error(f"Error retrieving processed data from MongoDB: {str(e)}")
            return None

    def get_symbols(self) -> List[str]:
        """Get list of available symbols"""
        try:
            symbols = self.historical_data.distinct('symbol')
            return list(symbols)
        except Exception as e:
            logger.error(f"Error retrieving symbols from MongoDB: {str(e)}")
            return []
        
    def save_news_data(self, symbol: str, news_data: Dict) -> bool:
        """Save news data to MongoDB"""
        try:
            news_data['symbol'] = symbol
            self.db['news_data'].insert_one(news_data)
            return True
        except Exception as e:
            logger.error(f"Error saving news data to MongoDB: {str(e)}")
            return False

    def get_latest_news(self, symbol: str) -> Optional[Dict]:
        """Get the most recent news data for a symbol"""
        try:
            news = self.db['news_data'].find_one(
                {'symbol': symbol},
                sort=[('timestamp', -1)]
            )
            return news
        except Exception as e:
            logger.error(f"Error retrieving news data from MongoDB: {str(e)}")
            return None

# Create global instance
db_service = MongoDBService()