"""
Base provider interface for market data providers.

All market data providers (Yahoo, Alpha Vantage, Finnhub, Tiingo) must implement this interface.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, List
import pandas as pd


class MarketDataProvider(ABC):
    """Abstract base class for market data providers."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize provider with optional API key.
        
        Args:
            api_key: API key for the provider (None for providers that don't require keys)
        """
        self.api_key = api_key
    
    @abstractmethod
    def get_ohlcv(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch OHLCV (Open, High, Low, Close, Volume) data for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            start: Start date in ISO format (YYYY-MM-DD)
            end: End date in ISO format (YYYY-MM-DD)
            interval: Data interval - '1d' for daily, '1m', '5m', '15m', '30m', '60m' for intraday
        
        Returns:
            DataFrame with columns: open, high, low, close, volume (lowercase)
            Index: DatetimeIndex
            
        Raises:
            ValueError: If symbol is invalid or data cannot be fetched
            PermissionError: If API key is missing or invalid
            ConnectionError: If rate limit is hit or network error occurs
        """
        pass
    
    @abstractmethod
    def get_quote(self, symbol: str) -> Dict:
        """
        Get current quote/market data for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dict with standardized quote data:
            {
                'lastPrice': float,
                'previousClose': float,
                'currency': str,
                'marketCap': float (optional),
                'pe': float (optional),
                'week52High': float (optional),
                'week52Low': float (optional)
            }
            
        Raises:
            ValueError: If symbol is invalid
            PermissionError: If API key is missing or invalid
        """
        pass
    
    @abstractmethod
    def get_news(self, symbol: str) -> List[Dict]:
        """
        Get news articles for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of dicts with standardized news data:
            [
                {
                    'title': str,
                    'link': str,
                    'publisher': str,
                    'providerPublishTime': int (unix timestamp),
                    'summary': str (optional)
                },
                ...
            ]
        """
        pass
    
    @classmethod
    @abstractmethod
    def requires_api_key(cls) -> bool:
        """Return whether this provider requires an API key."""
        pass
    
    @classmethod
    @abstractmethod
    def get_provider_name(cls) -> str:
        """Return the human-readable name of this provider."""
        pass
    
    def validate_api_key(self) -> bool:
        """
        Validate that the API key is present and valid.
        
        Returns:
            True if key is valid, False otherwise
        """
        if self.requires_api_key() and not self.api_key:
            return False
        return True
