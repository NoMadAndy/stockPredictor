"""
Finnhub provider implementation.

Requires API key. Get free key at: https://finnhub.io/register
"""
from typing import Dict, List, Optional
import pandas as pd
import requests
from datetime import datetime

from .base import MarketDataProvider


class FinnhubProvider(MarketDataProvider):
    """Finnhub data provider."""
    
    BASE_URL = "https://finnhub.io/api/v1"
    
    @classmethod
    def requires_api_key(cls) -> bool:
        return True
    
    @classmethod
    def get_provider_name(cls) -> str:
        return "Finnhub"
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        if not self.validate_api_key():
            raise PermissionError(
                "Finnhub requires an API key. "
                "Get a free key at https://finnhub.io/register"
            )
    
    def get_ohlcv(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from Finnhub.
        
        Note: Free tier has rate limits (60 calls/minute).
        Intraday data requires premium subscription.
        """
        try:
            # Convert dates to timestamps
            start_ts = int(datetime.fromisoformat(start).timestamp())
            end_ts = int(datetime.fromisoformat(end).timestamp())
            
            if interval == "1d":
                # Daily candles (available in free tier)
                resolution = "D"
            else:
                # Intraday candles (premium only)
                interval_map = {
                    "1m": "1",
                    "5m": "5",
                    "15m": "15",
                    "30m": "30",
                    "60m": "60",
                }
                resolution = interval_map.get(interval, "5")
            
            params = {
                "symbol": symbol.upper(),
                "resolution": resolution,
                "from": start_ts,
                "to": end_ts,
                "token": self.api_key,
            }
            
            response = requests.get(
                f"{self.BASE_URL}/stock/candle",
                params=params,
                timeout=10
            )
            
            if response.status_code == 401:
                raise PermissionError("Invalid Finnhub API key")
            
            if response.status_code == 429:
                raise ConnectionError(
                    "Finnhub API rate limit reached. "
                    "Free tier allows 60 calls/minute. Please wait."
                )
            
            if response.status_code != 200:
                raise ConnectionError(f"Finnhub API returned status {response.status_code}")
            
            data = response.json()
            
            # Check for errors
            if data.get("s") == "no_data":
                raise ValueError(
                    f"No data available for '{symbol}'. "
                    f"Symbol may be invalid or no data in specified range. "
                    f"Note: Intraday data requires Finnhub premium subscription."
                )
            
            if "c" not in data or not data["c"]:
                raise ValueError(f"Invalid response from Finnhub for symbol '{symbol}'")
            
            # Build DataFrame
            df = pd.DataFrame({
                'timestamp': data['t'],
                'open': data['o'],
                'high': data['h'],
                'low': data['l'],
                'close': data['c'],
                'volume': data['v'],
            })
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df = df.set_index('timestamp')
            df = df.sort_index()
            
            # Convert to numeric
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.dropna()
            
            if df.empty:
                raise ValueError(f"No valid data after cleaning for '{symbol}'")
            
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Network error connecting to Finnhub: {str(e)}")
        except Exception as e:
            if isinstance(e, (ValueError, PermissionError, ConnectionError)):
                raise
            raise ConnectionError(f"Error fetching data from Finnhub: {str(e)}")
    
    def get_quote(self, symbol: str) -> Dict:
        """Get current quote from Finnhub."""
        try:
            params = {
                "symbol": symbol.upper(),
                "token": self.api_key,
            }
            
            response = requests.get(
                f"{self.BASE_URL}/quote",
                params=params,
                timeout=10
            )
            
            if response.status_code == 401:
                raise PermissionError("Invalid Finnhub API key")
            
            if response.status_code == 429:
                raise ConnectionError("Finnhub API rate limit reached")
            
            data = response.json()
            
            if not data or data.get('c') == 0:
                raise ValueError(f"No quote data available for '{symbol}'")
            
            return {
                'lastPrice': float(data.get('c', 0)),  # current price
                'previousClose': float(data.get('pc', 0)),  # previous close
                'currency': 'USD',  # Finnhub primarily provides USD data
                'marketCap': None,  # Use company profile endpoint for this
                'pe': None,
                'week52High': float(data.get('h', 0)) if data.get('h') else None,  # today's high
                'week52Low': float(data.get('l', 0)) if data.get('l') else None,  # today's low
            }
            
        except Exception as e:
            if isinstance(e, (ValueError, PermissionError, ConnectionError)):
                raise
            raise ValueError(f"Error fetching quote: {str(e)}")
    
    def get_news(self, symbol: str) -> List[Dict]:
        """Get news from Finnhub."""
        news_items = []
        
        try:
            params = {
                "symbol": symbol.upper(),
                "token": self.api_key,
            }
            
            response = requests.get(
                f"{self.BASE_URL}/company-news",
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                return []  # News is optional
            
            data = response.json()
            
            for item in data[:10]:
                news_items.append({
                    'title': item.get('headline'),
                    'link': item.get('url'),
                    'publisher': item.get('source'),
                    'providerPublishTime': item.get('datetime'),
                    'summary': item.get('summary'),
                })
            
        except Exception:
            # News is optional, don't fail
            pass
        
        return news_items
