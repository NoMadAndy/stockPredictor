"""
Alpha Vantage provider implementation.

Requires API key. Get free key at: https://www.alphavantage.co/support/#api-key
"""
from typing import Dict, List, Optional
import pandas as pd
import requests
from datetime import datetime, timedelta

from .base import MarketDataProvider


class AlphaVantageProvider(MarketDataProvider):
    """Alpha Vantage data provider."""
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    @classmethod
    def requires_api_key(cls) -> bool:
        return True
    
    @classmethod
    def get_provider_name(cls) -> str:
        return "Alpha Vantage"
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        if not self.validate_api_key():
            raise PermissionError(
                "Alpha Vantage requires an API key. "
                "Get a free key at https://www.alphavantage.co/support/#api-key"
            )
    
    def get_ohlcv(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from Alpha Vantage.
        
        Note: Alpha Vantage has strict rate limits (5 calls/min for free tier).
        Intraday data is limited to the last 30 days.
        """
        try:
            if interval == "1d":
                # Daily data
                params = {
                    "function": "TIME_SERIES_DAILY",
                    "symbol": symbol,
                    "outputsize": "full",
                    "apikey": self.api_key,
                }
            else:
                # Intraday data
                interval_map = {
                    "1m": "1min",
                    "5m": "5min",
                    "15m": "15min",
                    "30m": "30min",
                    "60m": "60min",
                }
                av_interval = interval_map.get(interval, "5min")
                
                params = {
                    "function": "TIME_SERIES_INTRADAY",
                    "symbol": symbol,
                    "interval": av_interval,
                    "outputsize": "full",
                    "apikey": self.api_key,
                }
            
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            
            if response.status_code != 200:
                raise ConnectionError(f"Alpha Vantage API returned status {response.status_code}")
            
            data = response.json()
            
            # Check for API errors
            if "Error Message" in data:
                raise ValueError(f"Invalid symbol '{symbol}' or API error: {data['Error Message']}")
            
            if "Note" in data:
                raise ConnectionError(
                    "Alpha Vantage API rate limit reached. "
                    "Free tier allows 5 calls/minute and 100 calls/day. "
                    "Please wait or upgrade your plan."
                )
            
            if "Information" in data:
                raise ConnectionError(f"Alpha Vantage API limit: {data['Information']}")
            
            # Extract time series data
            if interval == "1d":
                time_series_key = "Time Series (Daily)"
            else:
                time_series_key = f"Time Series ({params['interval']})"
            
            if time_series_key not in data:
                available_keys = list(data.keys())
                raise ValueError(f"Unexpected API response. Available keys: {available_keys}")
            
            time_series = data[time_series_key]
            
            # Convert to DataFrame
            df = pd.DataFrame.from_dict(time_series, orient='index')
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            
            # Standardize column names
            column_map = {
                '1. open': 'open',
                '2. high': 'high',
                '3. low': 'low',
                '4. close': 'close',
                '5. volume': 'volume',
            }
            df = df.rename(columns=column_map)
            
            # Convert to numeric
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Filter by date range
            start_dt = pd.to_datetime(start)
            end_dt = pd.to_datetime(end)
            df = df[(df.index >= start_dt) & (df.index <= end_dt)]
            
            if df.empty:
                raise ValueError(
                    f"No data available for '{symbol}' in the specified date range. "
                    f"Note: Alpha Vantage intraday data is limited to ~30 days."
                )
            
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Network error connecting to Alpha Vantage: {str(e)}")
        except Exception as e:
            if isinstance(e, (ValueError, PermissionError, ConnectionError)):
                raise
            raise ConnectionError(f"Error fetching data from Alpha Vantage: {str(e)}")
    
    def get_quote(self, symbol: str) -> Dict:
        """Get current quote from Alpha Vantage."""
        try:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.api_key,
            }
            
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            data = response.json()
            
            if "Error Message" in data:
                raise ValueError(f"Invalid symbol '{symbol}'")
            
            if "Note" in data or "Information" in data:
                raise ConnectionError("Alpha Vantage API rate limit reached")
            
            global_quote = data.get("Global Quote", {})
            
            if not global_quote:
                raise ValueError(f"No quote data available for '{symbol}'")
            
            return {
                'lastPrice': float(global_quote.get('05. price', 0)),
                'previousClose': float(global_quote.get('08. previous close', 0)),
                'currency': 'USD',  # Alpha Vantage primarily provides USD data
                'marketCap': None,  # Not provided by this endpoint
                'pe': None,
                'week52High': float(global_quote.get('03. high', 0)) if global_quote.get('03. high') else None,
                'week52Low': float(global_quote.get('04. low', 0)) if global_quote.get('04. low') else None,
            }
            
        except Exception as e:
            if isinstance(e, (ValueError, ConnectionError)):
                raise
            raise ValueError(f"Error fetching quote: {str(e)}")
    
    def get_news(self, symbol: str) -> List[Dict]:
        """
        Get news from Alpha Vantage.
        
        Note: News & Sentiments API requires premium subscription.
        Returns empty list for now.
        """
        # Alpha Vantage news requires premium tier
        return []
