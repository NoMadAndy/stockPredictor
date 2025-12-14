"""
Provider factory and registry for market data providers.
"""
from typing import Dict, Optional, Type
from .base import MarketDataProvider
from .yahoo import YahooFinanceProvider
from .alpha_vantage import AlphaVantageProvider
from .finnhub import FinnhubProvider
from .tiingo import TiingoProvider


# Registry of all available providers
PROVIDERS: Dict[str, Type[MarketDataProvider]] = {
    "yahoo": YahooFinanceProvider,
    "alpha_vantage": AlphaVantageProvider,
    "finnhub": FinnhubProvider,
    "tiingo": TiingoProvider,
}


def get_provider(provider_name: str, api_key: Optional[str] = None) -> MarketDataProvider:
    """
    Factory function to get a provider instance.
    
    Args:
        provider_name: Name of the provider ('yahoo', 'alpha_vantage', 'finnhub', 'tiingo')
        api_key: API key for the provider (None for Yahoo)
    
    Returns:
        Instance of the requested provider
        
    Raises:
        ValueError: If provider name is not recognized
        PermissionError: If API key is required but not provided
    """
    provider_name = provider_name.lower()
    
    if provider_name not in PROVIDERS:
        available = ", ".join(PROVIDERS.keys())
        raise ValueError(
            f"Unknown provider '{provider_name}'. "
            f"Available providers: {available}"
        )
    
    provider_class = PROVIDERS[provider_name]
    
    return provider_class(api_key=api_key)


def list_providers() -> list:
    """
    List all available providers with their metadata.
    
    Returns:
        List of dicts with provider information
    """
    providers_info = []
    
    for key, provider_class in PROVIDERS.items():
        providers_info.append({
            "key": key,
            "name": provider_class.get_provider_name(),
            "requires_key": provider_class.requires_api_key(),
        })
    
    return providers_info


__all__ = [
    "MarketDataProvider",
    "YahooFinanceProvider",
    "AlphaVantageProvider",
    "FinnhubProvider",
    "TiingoProvider",
    "get_provider",
    "list_providers",
    "PROVIDERS",
]
