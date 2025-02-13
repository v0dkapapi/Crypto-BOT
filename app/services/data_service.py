import logging
import os
from typing import Dict, List, Optional
import pandas as pd
import requests
from datetime import datetime, timedelta
import ta
from services.db_service import db_service
from config.config import config

logger = logging.getLogger(__name__)

class CryptoDataService:
    def __init__(self):
        self.api_key = config.api.alpha_vantage_key
        self.base_url = config.api.base_url
        self.session = requests.Session()
        
        # Create data directories if they don't exist
        self.data_dir = os.path.join(os.getcwd(), 'data')
        self.raw_data_dir = os.path.join(self.data_dir, 'raw')
        self.processed_data_dir = os.path.join(self.data_dir, 'processed')
        
        os.makedirs(self.raw_data_dir, exist_ok=True)
        os.makedirs(self.processed_data_dir, exist_ok=True)

    def _get_csv_path(self, symbol: str, data_type: str) -> str:
        """Get the path for a CSV file"""
        if data_type == 'raw':
            return os.path.join(self.raw_data_dir, f"{symbol}_historical.csv")
        return os.path.join(self.processed_data_dir, f"{symbol}_processed.csv")

    def _should_update_data(self, symbol: str, update_interval_hours: int = 24) -> bool:
        """Check if data should be updated based on MongoDB timestamp"""
        latest_data = db_service.get_latest_processed_data(symbol)
        if not latest_data:
            return True
            
        last_update = latest_data['timestamp']
        elapsed_time = datetime.now() - last_update
        return elapsed_time.total_seconds() > (update_interval_hours * 3600)
    
    def _prepare_data_for_mongodb(self, df: pd.DataFrame) -> dict:
        """Convert DataFrame to MongoDB-compatible format"""
        # Convert DataFrame to dictionary with string dates
        data_dict = {}
        for idx, row in df.iterrows():
            date_str = idx.strftime('%Y-%m-%d %H:%M:%S')
            # Convert numpy/pandas types to native Python types
            row_dict = {}
            for key, value in row.items():
                if pd.isna(value):
                    row_dict[key] = None
                else:
                    row_dict[key] = float(value)
            data_dict[date_str] = row_dict
        return data_dict

    def fetch_and_save_historical_data(self, symbol: str = 'BTC', 
                                 market: str = 'USD', 
                                 force_update: bool = False) -> Optional[pd.DataFrame]:
        """Fetch historical data and save to both CSV and MongoDB"""
        csv_path = self._get_csv_path(symbol, 'raw')
        
        # Check if we need to update the data
        if not force_update and not self._should_update_data(symbol):
            logger.info(f"Loading cached data for {symbol}")
            latest_data = db_service.get_latest_historical_data(symbol)
            if latest_data:
                # Convert string dates back to datetime index
                data_dict = latest_data['data']
                df = pd.DataFrame.from_dict(data_dict, orient='index')
                df.index = pd.to_datetime(df.index)
                return df

        try:
            params = {
                'function': 'DIGITAL_CURRENCY_DAILY',
                'symbol': symbol,
                'market': market,
                'apikey': self.api_key
            }
            print("Hitting the endpoint")
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if 'Time Series (Digital Currency Daily)' not in data:
                logger.error(f"Unexpected response format for {symbol}: {data}")
                return None
            
            df = pd.DataFrame.from_dict(
                data['Time Series (Digital Currency Daily)'],
                orient='index'
            )
            
            # Clean column names and convert to numeric
            df.columns = [col.split('. ')[1] for col in df.columns]
            df = df.apply(pd.to_numeric)
            
            # Add date as index
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            
            # Save to CSV
            logger.info(f"Saving data for {symbol} to CSV")
            df.to_csv(csv_path)
            
            # Save to MongoDB with prepared data
            logger.info(f"Saving data for {symbol} to MongoDB")
            mongo_data = self._prepare_data_for_mongodb(df)
            db_service.save_historical_data(symbol, {
                'data': mongo_data,
                'market': market
            })
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            # Try to load cached data
            latest_data = db_service.get_latest_historical_data(symbol)
            if latest_data:
                data_dict = latest_data['data']
                df = pd.DataFrame.from_dict(data_dict, orient='index')
                df.index = pd.to_datetime(df.index)
                return df
            return None
        
    def _load_data_from_mongodb(self, mongodb_data: dict) -> pd.DataFrame:
        """Convert MongoDB data back to DataFrame with proper datetime index"""
        if not mongodb_data or 'data' not in mongodb_data:
            return None
            
        # Convert the data back to DataFrame
        df_dict = mongodb_data['data']
        df = pd.DataFrame.from_dict(df_dict, orient='index')
        
        # Convert index to datetime
        df.index = pd.to_datetime(df.index)
        
        # Sort by date
        df = df.sort_index()
        
        return df
    
    def calculate_technical_indicators(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Calculate technical indicators and save to MongoDB"""
        try:
            if 'close' in df.columns:
                # RSI
                df['RSI'] = ta.momentum.RSIIndicator(df['close']).rsi()
                
                # MACD
                macd = ta.trend.MACD(df['close'])
                df['MACD'] = macd.macd()
                df['MACD_Signal'] = macd.macd_signal()
                df['MACD_Hist'] = macd.macd_diff()
                
                # Moving Averages
                df['MA20'] = ta.trend.SMAIndicator(df['close'], window=20).sma_indicator()
                df['MA50'] = ta.trend.SMAIndicator(df['close'], window=50).sma_indicator()
                df['MA200'] = ta.trend.SMAIndicator(df['close'], window=200).sma_indicator()
                
                # Bollinger Bands
                bollinger = ta.volatility.BollingerBands(df['close'])
                df['BB_Upper'] = bollinger.bollinger_hband()
                df['BB_Middle'] = bollinger.bollinger_mavg()
                df['BB_Lower'] = bollinger.bollinger_lband()
                
                # Save to CSV and MongoDB
                processed_csv_path = self._get_csv_path(symbol, 'processed')
                df.to_csv(processed_csv_path)
                
                # Prepare data for MongoDB
                mongo_data = self._prepare_data_for_mongodb(df)
                
                # Save to MongoDB with last indicators
                db_service.save_processed_data(symbol, {
                    'data': mongo_data,
                    'indicators': {
                        'last_rsi': float(df['RSI'].iloc[-1]),
                        'last_macd': float(df['MACD'].iloc[-1]),
                        'last_macd_signal': float(df['MACD_Signal'].iloc[-1])
                    }
                })
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {str(e)}")
            return df

    def get_historical_data(self, symbol: str = 'BTC', 
                       market: str = 'USD', 
                       force_update: bool = False) -> Optional[pd.DataFrame]:
        """Get historical data from MongoDB or API"""
        if not force_update:
            latest_data = db_service.get_latest_processed_data(symbol)
            if latest_data and not self._should_update_data(symbol):
                return self._load_data_from_mongodb(latest_data)
        
        df = self.fetch_and_save_historical_data(symbol, market, force_update)
        if df is not None:
            return self.calculate_technical_indicators(df, symbol)
        return None

    def get_market_summary(self, symbol: str = 'BTC', force_update: bool = False) -> Dict:
        """Get market summary from MongoDB or calculate if needed"""
        try:
            df = self.get_historical_data(symbol, force_update=force_update)
            if df is None:
                return {}
            
            current_price = df['close'].iloc[-1]
            prev_day_price = df['close'].iloc[-2]
            
            summary = {
                'price': current_price,
                'price_change_24h': ((current_price - prev_day_price) / prev_day_price) * 100,
                'rsi': df['RSI'].iloc[-1],
                'macd_signal': 'bullish' if df['MACD_Hist'].iloc[-1] > 0 else 'bearish',
                'ma_signal': 'bullish' if current_price > df['MA50'].iloc[-1] else 'bearish',
                'volume_24h': df['volume'].iloc[-1],
                'timestamp': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating market summary for {symbol}: {str(e)}")
            return {}

    def get_multi_symbol_data(self, symbols: List[str], force_update: bool = False) -> Dict[str, Dict]:
        """Get data for multiple symbols"""
        return {
            symbol: self.get_market_summary(symbol, force_update)
            for symbol in symbols
        }

# Create global instance
crypto_data_service = CryptoDataService()