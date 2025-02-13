import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

from services.data_service import crypto_data_service
from services.analysis_service import analysis_service
from services.llm_service import llm_service
from services.forecast_service import forecast_service
from config.config import config

# Page configuration
st.set_page_config(
    page_title="Crypto Assistant",
    page_icon="📈",
    layout="wide"
)

# Initialize session state
if 'selected_crypto' not in st.session_state:
    st.session_state['selected_crypto'] = 'BTC'
if 'force_update' not in st.session_state:
    st.session_state['force_update'] = False
if 'time_range' not in st.session_state:
    st.session_state['time_range'] = '1M'
if 'chat_messages' not in st.session_state:
    st.session_state['chat_messages'] = []

# Cache functions
@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_ai_analysis(selected_crypto):
    return analysis_service.generate_market_analysis(selected_crypto)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_market_data(selected_crypto, force_update=False):
    return crypto_data_service.get_market_summary(selected_crypto, force_update)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_historical_data(selected_crypto):
    return crypto_data_service.get_historical_data(selected_crypto)

@st.cache_data(ttl=1800)  # Cache for 30 minutes
def get_forecast_data(df, horizon):
    return forecast_service.generate_forecast(df=df, h=horizon)

def filter_data_by_range(df, time_range):
    """Filter dataframe based on selected time range"""
    if df is None or df.empty:
        return None
        
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    end_date = pd.Timestamp.now()
    if time_range == '1D':
        start_date = end_date - pd.Timedelta(days=1)
    elif time_range == '1W':
        start_date = end_date - pd.Timedelta(weeks=1)
    elif time_range == '1M':
        start_date = end_date - pd.Timedelta(days=30)
    elif time_range == '3M':
        start_date = end_date - pd.Timedelta(days=90)
    elif time_range == '6M':
        start_date = end_date - pd.Timedelta(days=180)
    else:  # 1Y
        start_date = end_date - pd.Timedelta(days=365)
    
    return df[df.index >= start_date]

def render_analysis_section(analysis_data: dict):
    """Render the market analysis section"""
    if not analysis_data:
        st.warning("Analysis data not available")
        return

    # LLM Analysis
    st.subheader("📊 AI Market Analysis")
    with st.expander("View Detailed AI Analysis", expanded=True):
        st.markdown(analysis_data.get('llm_analysis', 'Analysis not available'))
    
    # Technical Analysis and News in Tabs
    tab1, tab2, tab3 = st.tabs(["Technical Analysis", "Market Metrics", "News"])
    
    with tab1:
        st.write("### Technical Indicators")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "RSI Condition",
                analysis_data['technical_indicators']['rsi_condition']
            )
        with col2:
            st.metric(
                "MACD Signal",
                analysis_data['technical_indicators']['macd_signal'].title()
            )
        with col3:
            st.metric(
                "Trend",
                analysis_data['price_analysis']['trend'].title()
            )
    
    with tab2:
        st.write("### Market Metrics")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Price Change (24h)",
                f"{analysis_data['price_analysis']['price_change_24h']:.2f}%"
            )
        with col2:
            st.metric(
                "Market Sentiment",
                analysis_data['market_sentiment']['news_sentiment']
            )
    
    with tab3:
        st.write("### Recent News")
        for news in analysis_data['market_sentiment']['latest_news']:
            with st.expander(news['title'], expanded=False):
                st.write(f"**Source:** {news['source']}")
                st.write(f"**Published:** {news['timestamp']}")
                st.write(f"**Sentiment:** {news['sentiment_label']}")
                st.write(news['summary'])
                st.markdown(f"[Read more]({news['url']})")

def main():
    # Sidebar
    with st.sidebar:
        st.title("Crypto Assistant")
        selected_crypto = st.selectbox(
            "Select Cryptocurrency",
            options=config.crypto.default_symbols,
            key='selected_crypto'
        )
        
        if st.button("Force Update Data"):
            st.session_state['force_update'] = True
            st.cache_data.clear()
        
        st.divider()
        
        # Time range selector
        time_range = st.selectbox(
            "Select Time Range",
            options=['1D', '1W', '1M', '3M', '6M', '1Y'],
            index=2,
            key='time_range'
        )
        
        # Indicator selector
        indicators = st.multiselect(
            "Select Technical Indicators",
            options=['RSI', 'MACD', 'Moving Averages', 'Bollinger Bands'],
            default=['RSI', 'MACD']
        )

    # Main content
    col1, col2, col3, col4 = st.columns(4)
    
    # Fetch market data using cached function
    market_data = get_market_data(selected_crypto, force_update=st.session_state['force_update'])
    
    if st.session_state['force_update']:
        st.session_state['force_update'] = False

    # Display metrics
    with col1:
        st.metric(
            "Price",
            f"${market_data.get('price', 0):,.2f}",
            f"{market_data.get('price_change_24h', 0):.2f}%"
        )
    
    with col2:
        rsi_value = market_data.get('rsi', 0)
        rsi_color = (
            "🔴" if rsi_value > 70 else 
            "🟢" if rsi_value < 30 else 
            "⚪"
        )
        st.metric(
            "RSI",
            f"{rsi_color} {rsi_value:.2f}",
            "Overbought" if rsi_value > 70 else "Oversold" if rsi_value < 30 else "Neutral"
        )
    
    with col3:
        macd_signal = market_data.get('macd_signal', 'N/A')
        signal_color = "🟢" if macd_signal == 'bullish' else "🔴"
        st.metric(
            "MACD Signal",
            f"{signal_color} {macd_signal.title()}"
        )
    
    with col4:
        st.metric(
            "24h Volume",
            f"${market_data.get('volume_24h', 0):,.0f}"
        )

    # Create main tabs
    tab1, tab2, tab3 = st.tabs(["📈 Charts", "🔮 Forecast", "🤖 AI Analysis"])
    
    with tab1:
        # Price chart
        st.subheader(f"{selected_crypto}/USD Price Chart")
        df = get_historical_data(selected_crypto)
        df = filter_data_by_range(df, st.session_state['time_range'])
        
        if df is not None:
            # Create price chart
            fig = go.Figure()
            
            # Add candlestick chart
            fig.add_trace(go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name=selected_crypto
            ))
            
            # Add indicators based on selection
            if 'Moving Averages' in indicators:
                ma_colors = {'MA20': 'blue', 'MA50': 'orange', 'MA200': 'red'}
                for ma, color in ma_colors.items():
                    if ma in df.columns:
                        fig.add_trace(go.Scatter(
                            x=df.index, 
                            y=df[ma],
                            name=ma, 
                            line=dict(color=color, width=1)
                        ))
            
            if 'Bollinger Bands' in indicators:
                for band, color in [('BB_Upper', 'gray'), ('BB_Lower', 'gray')]:
                    if band in df.columns:
                        fig.add_trace(go.Scatter(
                            x=df.index, 
                            y=df[band],
                            name=band, 
                            line=dict(color=color, width=1, dash='dash')
                        ))
            
            # Update layout
            fig.update_layout(
                height=600,
                template='plotly_dark',
                xaxis_rangeslider_visible=False,
                showlegend=True,
                yaxis_title='Price (USD)',
                xaxis_title='Date'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Display technical indicators in tabs if selected
            if 'RSI' in indicators or 'MACD' in indicators:
                indicator_tab1, indicator_tab2 = st.tabs(['RSI', 'MACD'])
                
                with indicator_tab1:
                    if 'RSI' in indicators:
                        fig_rsi = go.Figure()
                        fig_rsi.add_trace(go.Scatter(
                            x=df.index, 
                            y=df['RSI'],
                            name='RSI', 
                            line=dict(color='purple', width=2)
                        ))
                        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
                        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
                        fig_rsi.update_layout(
                            height=300, 
                            template='plotly_dark',
                            yaxis_title='RSI',
                            xaxis_title='Date'
                        )
                        st.plotly_chart(fig_rsi, use_container_width=True)
                
                with indicator_tab2:
                    if 'MACD' in indicators:
                        fig_macd = go.Figure()
                        fig_macd.add_trace(go.Scatter(
                            x=df.index, 
                            y=df['MACD'],
                            name='MACD', 
                            line=dict(color='blue', width=2)
                        ))
                        fig_macd.add_trace(go.Scatter(
                            x=df.index, 
                            y=df['MACD_Signal'],
                            name='Signal', 
                            line=dict(color='orange', width=2)
                        ))
                        fig_macd.add_bar(
                            x=df.index, 
                            y=df['MACD_Hist'],
                            name='Histogram'
                        )
                        fig_macd.update_layout(
                            height=300, 
                            template='plotly_dark',
                            yaxis_title='MACD',
                            xaxis_title='Date'
                        )
                        st.plotly_chart(fig_macd, use_container_width=True)

    with tab2:
        st.subheader(f"{selected_crypto}/USD Price Forecast")
        
        # Forecast settings
        col1, col2 = st.columns([3, 1])
        with col1:
            horizon = st.slider(
                "Forecast Horizon (Days)",
                min_value=7,
                max_value=90,
                value=30,
                step=1
            )
        
        # Get data and generate forecast
        df = get_historical_data(selected_crypto)
        if df is not None:
            with st.spinner("Generating forecast..."):
                # Use cached forecast function
                forecast_result = get_forecast_data(df, horizon)
                
                if forecast_result:
                    # Display forecast plot
                    forecast_fig = forecast_service.create_forecast_plot(
                        df, forecast_result, selected_crypto
                    )
                    if forecast_fig:
                        st.plotly_chart(forecast_fig, use_container_width=True)
                    
                    # Display forecast metrics
                    st.subheader("Forecast Analysis")
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        # Display forecast summary
                        st.markdown(forecast_service.get_forecast_summary(forecast_result))
                    
                    with col2:
                        metrics = forecast_result['metrics']
                        st.metric(
                            "Forecasted Price",
                            f"${metrics['forecast_end_price']:,.2f}",
                            f"{metrics['price_change']:,.2f}%"
                        )
                else:
                    st.error("Failed to generate forecast. Please try again.")
        else:
            st.error("Failed to fetch historical data for forecasting.")
    
    with tab3:
        # AI Analysis
        analysis_data = get_ai_analysis(selected_crypto)
        render_analysis_section(analysis_data)

    # Chat Interface
    st.markdown("---")
    st.subheader("💬 Chat with AI Assistant")

    # Clear chat button at the top of chat section
    col1, col2 = st.columns([6,1])
    with col2:
        if st.button("Clear Chat", key="clear_chat"):
            st.session_state.chat_messages = []
            llm_service.reset_chat_memory()
            st.rerun()

    # Display chat messages
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask anything about the cryptocurrency market..."):
        # Add user message to chat history
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = llm_service.get_chat_response(prompt, market_data)
                st.markdown(response)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()