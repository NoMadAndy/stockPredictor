"""
Tiingo provider implementation.

Requires API key. Get free key at: https://www.tiingo.com/account/api/token
"""
from typing import Dict, List, Optional
import pandas as pd
import requests
from datetime import datetime

from .base import MarketDataProvider


class TiingoProvider(MarketDataProvider):
    """Tiingo data provider."""
    
    BASE_URL = "https://api.tiingo.com"
    
    @classmethod
    def requires_api_key(cls) -> bool:
        return True
    
    @classmethod
    def get_provider_name(cls) -> str:
        return "Tiingo"
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        if not self.validate_api_key():
            raise PermissionError(
                "Tiingo requires an API key. "
                "Get a free key at https://www.tiingo.com/account/api/token"
            )
    
    def _get_headers(self) -> Dict:
        """Get headers for Tiingo API requests."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.api_key}"
        }
    
    def get_ohlcv(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from Tiingo.
        
        Note: Intraday data (IEX) available in free tier but limited to US stocks.
        """
        try:
            symbol = symbol.upper()
            
            if interval == "1d":
                # Daily data (end-of-day)
                url = f"{self.BASE_URL}/tiingo/daily/{symbol}/prices"
                params = {
                    "startDate": start,
                    "endDate": end,
                    "format": "json",
                }
            else:
                # Intraday data (IEX)
                interval_map = {
                    "1m": "1min",
                    "5m": "5min",
                    "15m": "15min",
                    "30m": "30min",
                    "60m": "1hour",
                }
                tiingo_interval = interval_map.get(interval, "5min")
                
                url = f"{self.BASE_URL}/iex/{symbol}/prices"
                params = {
                    "startDate": start,
                    "endDate": end,
                    "resampleFreq": tiingo_interval,
                    "format": "json",
                }
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=10
            )
            
            if response.status_code == 401:
                raise PermissionError("Invalid Tiingo API key")
            
            if response.status_code == 404:
                raise ValueError(
                    f"Symbol '{symbol}' not found. "
                    f"Tiingo intraday (IEX) only supports US stocks."
                )
            
            if response.status_code == 429:
                raise ConnectionError(
                    "Tiingo API rate limit reached. "
                    "Free tier allows limited requests per hour. Please wait."
                )
            
            if response.status_code != 200:
                raise ConnectionError(f"Tiingo API returned status {response.status_code}")
            
            data = response.json()
            
            if not data:
                raise ValueError(
                    f"No data available for '{symbol}' in the specified range. "
                    f"For intraday data, ensure the symbol is a US stock supported by IEX."
                )
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Standardize column names
            if interval == "1d":
                column_map = {
                    'date': 'timestamp',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume',
                }
            else:
                column_map = {
                    'date': 'timestamp',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume',
                }
            
            df = df.rename(columns=column_map)
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
            df = df.sort_index()
            
            # Ensure we have required columns
            required = ['open', 'high', 'low', 'close', 'volume']
            missing = [col for col in required if col not in df.columns]
            if missing:
                raise ValueError(f"Missing required columns: {missing}")
            
            # Convert to numeric
            for col in required:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.dropna(subset=['open', 'high', 'low', 'close'])
            
            if df.empty:
                raise ValueError(f"No valid data after cleaning for '{symbol}'")
            
            return df[required]
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Network error connecting to Tiingo: {str(e)}")
        except Exception as e:
            if isinstance(e, (ValueError, PermissionError, ConnectionError)):
                raise
            raise ConnectionError(f"Error fetching data from Tiingo: {str(e)}")
    
    def get_quote(self, symbol: str) -> Dict:
        """Get current quote from Tiingo."""
        try:
            symbol = symbol.upper()
            url = f"{self.BASE_URL}/iex/{symbol}"
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code == 401:
                raise PermissionError("Invalid Tiingo API key")
            
            if response.status_code == 404:
                raise ValueError(f"Symbol '{symbol}' not found")
            
            if response.status_code == 429:
                raise ConnectionError("Tiingo API rate limit reached")
            
            data = response.json()
            
            if not data or len(data) == 0:
                raise ValueError(f"No quote data available for '{symbol}'")
            
            quote_data = data[0] if isinstance(data, list) else data
            
            return {
                'lastPrice': float(quote_data.get('last', 0) or quote_data.get('tngoLast', 0)),
                'previousClose': float(quote_data.get('prevClose', 0)),
                'currency': 'USD',  # Tiingo IEX is US stocks
                'marketCap': None,  # Use meta endpoint for this
                'pe': None,
                'week52High': float(quote_data.get('high', 0)) if quote_data.get('high') else None,
                'week52Low': float(quote_data.get('low', 0)) if quote_data.get('low') else None,
            }
            
        except Exception as e:
            if isinstance(e, (ValueError, PermissionError, ConnectionError)):
                raise
            raise ValueError(f"Error fetching quote: {str(e)}")
    
    def get_news(self, symbol: str) -> List[Dict]:
        """
        Get news from Tiingo.
        
        Note: News API available but requires separate endpoint.
        """
        news_items = []
        
        try:
            symbol = symbol.upper()
            url = f"{self.BASE_URL}/tiingo/news"
            params = {
                "tickers": symbol,
                "limit": 10,
            }
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                return []  # News is optional
            
            data = response.json()
            
            for item in data:
                # Convert publishedDate to timestamp
                pub_time = None
                pub_str = item.get('publishedDate')
                if pub_str:
                    try:
                        dt = datetime.fromisoformat(pub_str.replace('Z', '+00:00'))
                        pub_time = int(dt.timestamp())
                    except Exception:
                        pass
                
                news_items.append({
                    'title': item.get('title'),
                    'link': item.get('url'),
                    'publisher': item.get('source'),
                    'providerPublishTime': pub_time,
                    'summary': item.get('description'),
                })
            
        except Exception:
            # News is optional, don't fail
            pass
        
        return news_items
