import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from typing import List, Optional

def render_market_metrics(market_summary: dict):
    """Render market metrics in columns"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Price",
            f"${market_summary.get('price', 0):,.2f}",
            f"{market_summary.get('price_change_24h', 0):.2f}%"
        )
    
    with col2:
        st.metric(
            "RSI",
            f"{market_summary.get('rsi', 0):.2f}",
            "Overbought" if market_summary.get('rsi', 0) > 70 else "Oversold" if market_summary.get('rsi', 0) < 30 else "Neutral"
        )
    
    with col3:
        st.metric(
            "MACD Signal",
            market_summary.get('macd_signal', 'N/A').title()
        )
    
    with col4:
        st.metric(
            "24h Volume",
            f"${market_summary.get('volume_24h', 0):,.0f}"
        )

def create_price_chart(df: pd.DataFrame, selected_crypto: str, indicators: List[str]) -> go.Figure:
    """Create price chart with selected indicators"""
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
    
    # Add indicators
    if 'Moving Averages' in indicators:
        for ma in ['MA20', 'MA50', 'MA200']:
            if ma in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index, y=df[ma],
                    name=ma, line=dict(width=1)
                ))
    
    if 'Bollinger Bands' in indicators:
        for band in ['BB_Upper', 'BB_Middle', 'BB_Lower']:
            if band in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index, y=df[band],
                    name=band, line=dict(width=1, dash='dash')
                ))
    
    # Update layout
    fig.update_layout(
        height=600,
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        showlegend=True
    )
    
    return fig

def create_indicator_charts(df: pd.DataFrame, indicators: List[str]) -> dict:
    """Create technical indicator charts"""
    charts = {}
    
    if 'RSI' in indicators:
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(
            x=df.index, y=df['RSI'],
            name='RSI', line=dict(color='purple', width=2)
        ))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
        fig_rsi.update_layout(height=300, template='plotly_dark')
        charts['RSI'] = fig_rsi
    
    if 'MACD' in indicators:
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(
            x=df.index, y=df['MACD'],
            name='MACD', line=dict(color='blue', width=2)
        ))
        fig_macd.add_trace(go.Scatter(
            x=df.index, y=df['MACD_Signal'],
            name='Signal', line=dict(color='orange', width=2)
        ))
        fig_macd.add_bar(
            x=df.index, y=df['MACD_Hist'],
            name='Histogram'
        )
        fig_macd.update_layout(height=300, template='plotly_dark')
        charts['MACD'] = fig_macd
    
    return charts

def render_dashboard(
    selected_crypto: str,
    market_summary: dict,
    df: Optional[pd.DataFrame],
    indicators: List[str]
):
    """Render complete dashboard"""
    # Render metrics
    render_market_metrics(market_summary)
    
    # Render price chart
    st.subheader(f"{selected_crypto}/USD Price Chart")
    if df is not None:
        price_chart = create_price_chart(df, selected_crypto, indicators)
        st.plotly_chart(price_chart, use_container_width=True)
        
        # Render indicator charts
        if any(ind in indicators for ind in ['RSI', 'MACD']):
            indicator_charts = create_indicator_charts(df, indicators)
            
            # Create tabs for indicators
            if indicator_charts:
                tabs = st.tabs(list(indicator_charts.keys()))
                for tab, (name, chart) in zip(tabs, indicator_charts.items()):
                    with tab:
                        st.plotly_chart(chart, use_container_width=True)