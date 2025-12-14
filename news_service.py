# news_service.py
import os
from datetime import datetime

import yfinance as yf
import requests

from utils import suppress_yfinance_output


# ---------------------------------------------------------
# Logging-Helfer
# ---------------------------------------------------------


def _log(logger, msg: str):
    if logger:
        logger(msg)


# ---------------------------------------------------------
# API-Key Laden (stabil, relativ zum Skript)
# ---------------------------------------------------------

_NEWS_API_KEY_CACHE = None


def _load_news_api_key(logger=None) -> str | None:
    """
    Lädt den NewsAPI-Key möglichst robust.

    Reihenfolge / Suchlogik:
    1. NEWSAPI_KEY_FILE (wenn gesetzt)
       - wenn relativ: relativ zum Verzeichnis dieser Datei
       - wenn absolut: direkt so
    2. news_api_key.txt im gleichen Verzeichnis wie news_service.py
    3. news_api_key.txt im aktuellen Arbeitsverzeichnis
    4. Fallback: Umgebungsvariable NEWSAPI_KEY

    Rückgabe: API-Key als String oder None.
    """
    global _NEWS_API_KEY_CACHE
    if _NEWS_API_KEY_CACHE is not None:
        return _NEWS_API_KEY_CACHE

    script_dir = os.path.dirname(os.path.abspath(__file__))

    candidates = []

    # 1) NEWSAPI_KEY_FILE, falls gesetzt
    env_path = os.getenv("NEWSAPI_KEY_FILE")
    if env_path:
        if os.path.isabs(env_path):
            candidates.append(env_path)
        else:
            candidates.append(os.path.join(script_dir, env_path))

    # 2) news_api_key.txt im gleichen Verzeichnis wie dieses Skript
    candidates.append(os.path.join(script_dir, "news_api_key.txt"))

    # 3) news_api_key.txt im aktuellen Arbeitsverzeichnis (fallback)
    candidates.append("news_api_key.txt")

    for path in candidates:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    key = f.read().strip()
                    if key:
                        _NEWS_API_KEY_CACHE = key
                        _log(logger, f"NewsAPI-Key aus Datei geladen: {path}")
                        return key
        except Exception as e:
            _log(logger, f"Fehler beim Lesen der NewsAPI-Key-Datei '{path}': {e}")

    # 4) Fallback: Umgebungsvariable
    key_env = os.getenv("NEWSAPI_KEY")
    if key_env:
        _NEWS_API_KEY_CACHE = key_env.strip()
        _log(logger, "NewsAPI-Key aus Umgebungsvariable NEWSAPI_KEY geladen.")
        return _NEWS_API_KEY_CACHE

    _log(
        logger,
        "Kein NewsAPI-Key gefunden (Dateien + Umgebungsvariable geprüft). "
        "Externe News werden übersprungen.",
    )
    return None


# ---------------------------------------------------------
# Symbol-Name
# ---------------------------------------------------------


def get_symbol_name(symbol: str, logger=None) -> str:
    """Versucht, den vollen Namen der Aktie über yfinance zu holen."""
    import json
    try:
        # Suppress yfinance error messages
        with suppress_yfinance_output():
            t = yf.Ticker(symbol)
            info = t.info or {}
        name = info.get("shortName") or info.get("longName")
        if name:
            return str(name)
    except json.JSONDecodeError:
        # JSON parsing error typically indicates invalid/delisted ticker
        _log(logger, f"Symbol '{symbol}' konnte nicht abgerufen werden (möglicherweise ungültig oder delisted)")
    except Exception as e:
        # Log other errors but don't raise - just return the symbol as fallback
        error_msg = str(e)
        if "No timezone found" in error_msg or "delisted" in error_msg.lower():
            _log(logger, f"Symbol '{symbol}' konnte nicht abgerufen werden (möglicherweise ungültig oder delisted)")
        else:
            _log(logger, f"get_symbol_name Fehler: {e}")
    return symbol


# ---------------------------------------------------------
# Zusätzliche News über NewsAPI.org
# ---------------------------------------------------------


def get_additional_news(symbol: str, symbol_name: str | None = None, logger=None):
    """
    Holt zusätzliche News über eine externe API (NewsAPI.org).

    Der API-Key wird aus Datei(en) bzw. optional aus der Umgebungsvariable geladen.
    Gibt eine Liste im gleichen Format wie yfinance-News zurück.
    """
    api_key = _load_news_api_key(logger=logger)
    news_items = []

    if not api_key:
        # Info wurde schon in _load_news_api_key geloggt
        return news_items

    query = symbol_name or symbol
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "language": "de",
            "sortBy": "publishedAt",
            "pageSize": 5,
            "apiKey": api_key,
        }

        r = requests.get(url, params=params, timeout=5)
        if r.status_code != 200:
            _log(logger, f"NewsAPI Antwort {r.status_code}: {r.text[:200]}")
            return news_items

        data = r.json()
        for art in data.get("articles", []):
            published_ts = None
            pub_str = art.get("publishedAt")
            if pub_str:
                try:
                    dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                    published_ts = int(dt.timestamp())
                except Exception:
                    published_ts = None

            news_items.append(
                {
                    "title": art.get("title"),
                    "link": art.get("url"),
                    "publisher": (art.get("source") or {}).get("name"),
                    "providerPublishTime": published_ts,
                    "summary": art.get("description") or art.get("content"),
                }
            )

        _log(logger, f"NewsAPI-Artikel geladen: {len(news_items)}")

    except Exception as e:
        _log(logger, f"NewsAPI Fehler: {e}")

    return news_items


# ---------------------------------------------------------
# Quote & kombinierte News
# ---------------------------------------------------------


def get_quote_and_news(symbol: str, logger=None):
    """
    Holt aktuelle Kennzahlen und News zu einem Symbol über yfinance
    UND (optional) externe News-Provider (NewsAPI.org).
    """
    quote = {}
    news_items = []

    try:
        # Suppress yfinance error messages
        with suppress_yfinance_output():
            t = yf.Ticker(symbol)

            # Quote
            fast = getattr(t, "fast_info", None)
            info = {}
            try:
                info = t.info or {}
            except Exception:
                info = {}

            # yfinance-News
            raw_news = []
            try:
                raw_news = getattr(t, "news", None) or []
            except Exception:
                raw_news = []
            if not raw_news:
                try:
                    raw_news = t.get_news() or []
                except Exception:
                    raw_news = []

        if fast is not None:
            last_price = getattr(fast, "last_price", None)
            if last_price is not None:
                quote["lastPrice"] = float(last_price)
            quote["currency"] = getattr(fast, "currency", info.get("currency"))
        else:
            lp = info.get("regularMarketPrice")
            quote["lastPrice"] = float(lp) if lp is not None else None
            quote["currency"] = info.get("currency")

        quote["previousClose"] = info.get("previousClose")
        quote["marketCap"] = info.get("marketCap")
        quote["pe"] = info.get("trailingPE")
        quote["week52High"] = info.get("fiftyTwoWeekHigh")
        quote["week52Low"] = info.get("fiftyTwoWeekLow")

        for item in raw_news[:5]:
            news_items.append(
                {
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "publisher": item.get("publisher"),
                    "providerPublishTime": item.get("providerPublishTime"),
                    "summary": item.get("summary") or item.get("content"),
                }
            )

        _log(
            logger,
            f"yfinance-News-Einträge geladen (roh): {len(raw_news)}, verwendbar: {len(news_items)}",
        )

        # externe News ergänzen
        symbol_name = (
            info.get("shortName")
            or info.get("longName")
            or get_symbol_name(symbol, logger=logger)
        )
        extra_news = get_additional_news(symbol, symbol_name, logger=logger)

        combined = news_items + extra_news
        dedup = []
        seen = set()
        for item in combined:
            title = item.get("title")
            link = item.get("link")
            if not title or not link:
                continue
            key = (title, link)
            if key in seen:
                continue
            seen.add(key)
            dedup.append(item)

        news_items = dedup[:8]
        _log(
            logger,
            f"Gesamt-News nach Merge & Dedupe: {len(news_items)} "
            f"(yfinance={len(raw_news)}, extern={len(extra_news)})",
        )

    except Exception as e:
        _log(logger, f"News/Quote konnten nicht geladen werden: {e}")

    return quote, news_items
