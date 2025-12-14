"""
Yahoo Finance provider implementation using yfinance.

No API key required.
"""
from typing import Dict, List, Optional
import pandas as pd
import yfinance as yf
from datetime import datetime

from .base import MarketDataProvider
# Import utils from parent package - this is intentional coupling
# as the suppress_yfinance_output utility is shared across the app
from utils import suppress_yfinance_output


class YahooFinanceProvider(MarketDataProvider):
    """Yahoo Finance data provider using yfinance library."""
    
    @classmethod
    def requires_api_key(cls) -> bool:
        return False
    
    @classmethod
    def get_provider_name(cls) -> str:
        return "Yahoo Finance"
    
    def get_ohlcv(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from Yahoo Finance.
        
        Args:
            symbol: Stock symbol
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            interval: '1d', '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h'
        
        Returns:
            DataFrame with lowercase columns: open, high, low, close, volume
        """
        # Map common intervals to yfinance format
        interval_map = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "60m": "60m",
            "1h": "1h",
            "1d": "1d",
        }
        
        yf_interval = interval_map.get(interval, interval)
        
        try:
            with suppress_yfinance_output():
                df = yf.download(
                    symbol,
                    start=start,
                    end=end,
                    interval=yf_interval,
                    progress=False,
                    auto_adjust=False,
                )
            
            if df is None or df.empty:
                raise ValueError(
                    f"No data returned for symbol '{symbol}'. "
                    f"Symbol may be invalid, delisted, or no data available for the given period."
                )
            
            # Handle MultiIndex columns (when multiple symbols or specific format)
            if isinstance(df.columns, pd.MultiIndex):
                # Try to extract just the data we need
                try:
                    df = df.xs(symbol, level=1, axis=1) if symbol in df.columns.get_level_values(1) else df.iloc[:, :5]
                except Exception:
                    # Flatten multiindex by taking first level
                    df.columns = df.columns.get_level_values(0)
            
            # Standardize column names to lowercase
            df.columns = df.columns.str.lower()
            
            # Ensure we have the required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing = [col for col in required_cols if col not in df.columns]
            
            if missing:
                # Try alternative column names
                col_map = {
                    'adj close': 'close',
                }
                df = df.rename(columns=col_map)
                
                # Check again
                missing = [col for col in required_cols if col not in df.columns]
                if 'volume' in missing and len(df.columns) == 4:
                    # Some intraday data might not have volume, add it
                    df['volume'] = 0
                    missing.remove('volume')
                
                if missing:
                    raise ValueError(f"Missing required columns: {missing}")
            
            # Select and order columns
            df = df[required_cols].copy()
            
            # Ensure datetime index
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            
            # Remove any NaN rows
            df = df.dropna(subset=['open', 'high', 'low', 'close'])
            
            if df.empty:
                raise ValueError(f"No valid data after cleaning for symbol '{symbol}'")
            
            return df
            
        except Exception as e:
            error_msg = str(e)
            if "No timezone found" in error_msg or "delisted" in error_msg.lower():
                raise ValueError(
                    f"Symbol '{symbol}' appears to be invalid or delisted. "
                    f"Please verify the ticker symbol."
                )
            elif "No data found" in error_msg:
                raise ValueError(
                    f"No data found for '{symbol}' in the specified time range. "
                    f"For intraday data, note that Yahoo Finance limits intraday history to ~60 days."
                )
            else:
                raise ConnectionError(f"Error fetching data from Yahoo Finance: {error_msg}")
    
    def get_quote(self, symbol: str) -> Dict:
        """Get current quote from Yahoo Finance."""
        try:
            with suppress_yfinance_output():
                ticker = yf.Ticker(symbol)
                fast_info = getattr(ticker, 'fast_info', None)
                info = {}
                try:
                    info = ticker.info or {}
                except Exception:
                    pass
            
            quote = {}
            
            # Get last price
            if fast_info is not None:
                last_price = getattr(fast_info, 'last_price', None)
                if last_price is not None:
                    quote['lastPrice'] = float(last_price)
                quote['currency'] = getattr(fast_info, 'currency', info.get('currency'))
            else:
                lp = info.get('regularMarketPrice') or info.get('currentPrice')
                quote['lastPrice'] = float(lp) if lp is not None else None
                quote['currency'] = info.get('currency')
            
            # Add other quote fields
            quote['previousClose'] = info.get('previousClose')
            quote['marketCap'] = info.get('marketCap')
            quote['pe'] = info.get('trailingPE')
            quote['week52High'] = info.get('fiftyTwoWeekHigh')
            quote['week52Low'] = info.get('fiftyTwoWeekLow')
            
            return quote
            
        except Exception as e:
            raise ValueError(f"Error fetching quote for '{symbol}': {str(e)}")
    
    def get_news(self, symbol: str) -> List[Dict]:
        """Get news from Yahoo Finance."""
        news_items = []
        
        try:
            with suppress_yfinance_output():
                ticker = yf.Ticker(symbol)
                
                # Try to get news
                raw_news = []
                try:
                    raw_news = getattr(ticker, 'news', None) or []
                except Exception:
                    pass
                
                if not raw_news:
                    try:
                        raw_news = ticker.get_news() or []
                    except Exception:
                        pass
            
            # Convert to standardized format
            for item in raw_news[:10]:
                news_items.append({
                    'title': item.get('title'),
                    'link': item.get('link'),
                    'publisher': item.get('publisher'),
                    'providerPublishTime': item.get('providerPublishTime'),
                    'summary': item.get('summary') or item.get('content'),
                })
            
        except Exception:
            # News is optional, don't fail if unavailable
            pass
        
        return news_items
