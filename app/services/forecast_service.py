import logging
from typing import Dict, Optional
import pandas as pd
from nixtla import NixtlaClient
import plotly.graph_objects as go
from datetime import datetime, timedelta
from config.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ForecastService:
    def __init__(self):
        self.client = NixtlaClient(api_key="")
    
    def prepare_data_for_forecast(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for forecast"""
        try:
            logger.info(f"Input DataFrame columns: {df.columns.tolist()}")
            logger.info(f"Input DataFrame shape: {df.shape}")
            
            # Create a new DataFrame with the required format
            forecast_df = pd.DataFrame()
            
            # Convert index to datetime if it's not already
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            
            # Create the forecast DataFrame
            forecast_df['ds'] = df.index
            forecast_df['y'] = df['close'].values  # Use .values to ensure proper assignment
            
            # Sort by date and reset index
            forecast_df = forecast_df.sort_values('ds').reset_index(drop=True)
            
            # Drop any NaN values
            forecast_df = forecast_df.dropna()
            
            logger.info(f"Prepared DataFrame columns: {forecast_df.columns.tolist()}")
            logger.info(f"Prepared DataFrame head:\n{forecast_df.head()}")
            logger.info(f"Number of NaN values in y: {forecast_df['y'].isna().sum()}")
            
            return forecast_df
            
        except Exception as e:
            logger.error(f"Error preparing forecast data: {str(e)}")
            return None

    def generate_forecast(self, 
                         df: pd.DataFrame, 
                         h: int = 14  # Reduced forecast horizon to avoid warnings
                         ) -> Dict:
        """Generate forecast using Nixtla"""
        try:
            # Validate input data
            if df is None or df.empty:
                logger.error("Input DataFrame is None or empty")
                return None

            if 'close' not in df.columns:
                logger.error("Close price column not found in input data")
                return None

            if df['close'].isna().all():
                logger.error("All close prices are NaN")
                return None
                
            # Prepare data
            forecast_df = self.prepare_data_for_forecast(df)
            if forecast_df is None:
                return None
                
            if forecast_df['y'].isna().any():
                logger.error("Target column contains NaN values after preparation")
                return None
                
            logger.info("Generating forecast with data shape: {}".format(forecast_df.shape))
            logger.info(f"Sample of prepared data:\n{forecast_df.head()}")
            
            # Generate forecast
            forecast = self.client.forecast(
                df=forecast_df,
                h=h,
                model='timegpt-1',
                time_col='ds',
                target_col='y',
                freq='D'
            )
            
            logger.info(f"Forecast result columns: {forecast.columns.tolist()}")
            
            # Calculate additional metrics using the 'TimeGPT' column
            last_price = df['close'].iloc[-1]
            forecast_mean = forecast['TimeGPT'].iloc[-1]  # Use 'TimeGPT' column
            price_change = ((forecast_mean - last_price) / last_price) * 100
            
            # Store the forecast with renamed column for consistency
            forecast_result = forecast.rename(columns={'TimeGPT': 'y'})
            
            return {
                'forecast_df': forecast_result,
                'metrics': {
                    'forecast_horizon': h,
                    'last_price': last_price,
                    'forecast_end_price': forecast_mean,
                    'price_change': price_change,
                    'forecast_dates': {
                        'start': forecast_result['ds'].min(),
                        'end': forecast_result['ds'].max()
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating forecast: {str(e)}")
            logger.error(f"DataFrame info: {df.info()}")
            return None

    def create_forecast_plot(self, 
                           historical_df: pd.DataFrame, 
                           forecast_result: Dict,
                           selected_crypto: str) -> go.Figure:
        """Create a plotly figure with historical data and forecast"""
        try:
            fig = go.Figure()
            
            # Add historical prices
            fig.add_trace(go.Scatter(
                x=historical_df.index,
                y=historical_df['close'],
                name='Historical',
                line=dict(color='blue')
            ))
            
            forecast_df = forecast_result['forecast_df']
            
            # Add forecast
            fig.add_trace(go.Scatter(
                x=forecast_df['ds'],
                y=forecast_df['y'],  # Use renamed column
                name='Forecast',
                line=dict(color='red', dash='dash')
            ))
            
            # Add confidence intervals if available
            for level in [80, 95]:
                low_col = f'low_{level}'
                high_col = f'high_{level}'
                if low_col in forecast_df.columns and high_col in forecast_df.columns:
                    fig.add_trace(go.Scatter(
                        x=forecast_df['ds'],
                        y=forecast_df[low_col],
                        name=f'{level}% Lower Bound',
                        line=dict(width=0),
                        showlegend=False
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=forecast_df['ds'],
                        y=forecast_df[high_col],
                        name=f'{level}% Confidence Interval',
                        fill='tonexty',
                        fillcolor=f'rgba(0, 100, 255, 0.{level-70})',
                        line=dict(width=0)
                    ))
            
            # Update layout
            fig.update_layout(
                title=f"{selected_crypto} Price Forecast",
                xaxis_title="Date",
                yaxis_title="Price (USD)",
                height=500,
                template='plotly_dark',
                hovermode='x unified',
                showlegend=True,
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01
                )
            )
            
            # Add range slider
            fig.update_xaxes(rangeslider_visible=True)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating forecast plot: {str(e)}")
            return None

    def get_forecast_summary(self, forecast_result: Dict) -> str:
        """Generate a summary of the forecast"""
        try:
            metrics = forecast_result['metrics']
            forecast_start = metrics['forecast_dates']['start'].strftime('%Y-%m-%d')
            forecast_end = metrics['forecast_dates']['end'].strftime('%Y-%m-%d')
            
            summary = f"""
            ### Forecast Summary
            
            **Period**: {forecast_start} to {forecast_end} ({metrics['forecast_horizon']} days)
            
            **Price Projections**:
            - Current Price: ${metrics['last_price']:,.2f}
            - Forecasted Price: ${metrics['forecast_end_price']:,.2f}
            - Expected Change: {metrics['price_change']:,.2f}%
            
            **Note**: This forecast is generated using TimeGPT and should be used as one of many tools for analysis.
            Past performance does not guarantee future results.
            """
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating forecast summary: {str(e)}")
            return "Unable to generate forecast summary"

# Create global instance
forecast_service = ForecastService()