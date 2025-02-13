import logging
from typing import Dict, List, Optional
from datetime import datetime
from langchain.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory

logger = logging.getLogger(__name__)

class CryptoLLMService:
    def __init__(self):
        # Initialize Ollama LLM
        self.llm = Ollama(model="llama3.2")
        
        # Initialize conversation memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create analysis prompt template
        self.analysis_prompt = PromptTemplate(
            input_variables=["price_data", "technical_indicators", "news_data", "market_data"],
            template="""
            As a cryptocurrency market analyst, provide a comprehensive analysis based on the following data:

            Price Information:
            {price_data}

            Technical Indicators:
            {technical_indicators}

            Recent News:
            {news_data}

            Market Statistics:
            {market_data}

            Please provide a detailed analysis covering:
            1. Current market sentiment
            2. Technical analysis interpretation
            3. Key price levels and trends
            4. Potential market scenarios
            5. Risk factors to consider

            Keep the analysis professional and data-driven.
            """
        )
        
        # Create chat prompt template with single input
        self.chat_prompt = PromptTemplate(
            input_variables=["input"],
            template="""
            You are a cryptocurrency trading assistant. Answer the following question 
            based on your knowledge and market understanding:

            Question: {input}

            Provide a clear and concise response focused on helpful information and analysis.
            If discussing price predictions, include appropriate disclaimers.
            """
        )
        
        # Initialize chains
        self.analysis_chain = LLMChain(
            llm=self.llm,
            prompt=self.analysis_prompt,
            verbose=True
        )
        
        self.chat_chain = LLMChain(
            llm=self.llm,
            prompt=self.chat_prompt,
            verbose=True
        )

    def generate_analysis(self, market_data: Dict, news_items: List[Dict]) -> str:
        """Generate comprehensive market analysis using LLM"""
        try:
            analysis = self.analysis_chain.run({
                "price_data": self._format_price_data(market_data),
                "technical_indicators": self._format_technical_indicators(market_data),
                "news_data": self._format_news_data(news_items),
                "market_data": self._format_market_data(market_data)
            })
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error generating analysis: {str(e)}")
            return "Sorry, I couldn't generate the analysis at the moment."

    def get_chat_response(self, user_message: str, market_context: Dict) -> str:
        """Get chat response using LLM"""
        try:
            # Create enhanced prompt with market context
            enhanced_message = f"""
            Current Market Context:
            - Price: ${market_context.get('price', 0):,.2f}
            - 24h Change: {market_context.get('price_change_24h', 0):.2f}%
            - RSI: {market_context.get('rsi', 0):.2f}
            - MACD Signal: {market_context.get('macd_signal', 'neutral')}

            User Question: {user_message}
            """
            
            response = self.chat_chain.run(input=enhanced_message)
            return response
            
        except Exception as e:
            logger.error(f"Error getting chat response: {str(e)}")
            return "I apologize, but I encountered an error processing your request."

    def _format_price_data(self, market_data: Dict) -> str:
        return f"""
        Current Price: ${market_data.get('price', 0):,.2f}
        24h Change: {market_data.get('price_change_24h', 0):.2f}%
        24h Volume: ${market_data.get('volume_24h', 0):,.2f}
        """

    def _format_technical_indicators(self, market_data: Dict) -> str:
        return f"""
        RSI: {market_data.get('rsi', 0):.2f}
        MACD Signal: {market_data.get('macd_signal', 'neutral')}
        Trend: {market_data.get('ma_signal', 'neutral')}
        """

    def _format_news_data(self, news_items: List[Dict]) -> str:
        news_text = "Recent News:\n"
        for item in news_items[:3]:  # Top 3 news items
            news_text += f"- {item['title']} (Sentiment: {item['sentiment_label']})\n"
        return news_text

    def _format_market_data(self, market_data: Dict) -> str:
        return f"""
        Market Cap Rank: {market_data.get('market_cap_rank', 'N/A')}
        Market Dominance: {market_data.get('market_dominance', 'N/A')}%
        Trading Volume Trend: {market_data.get('volume_trend', 'N/A')}
        """

    def reset_chat_memory(self):
        """Reset the conversation memory"""
        self.memory.clear()

# Create global instance
llm_service = CryptoLLMService()