import os
from datetime import datetime, timedelta

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit

from news_service import get_symbol_name, get_quote_and_news  # <--- NEU
from utils import suppress_yfinance_output
from providers import get_provider, list_providers
from provider_key_store import ProviderKeyStore, get_encryption_secret
from cache import market_data_cache, get_cache_key


# -------------------------------------------------------------------
# Custom Exceptions
# -------------------------------------------------------------------
class TickerDataError(Exception):
    """Raised when ticker data cannot be fetched (invalid, delisted, etc.)"""
    pass


# -------------------------------------------------------------------
# Flask + Socket.IO Setup
# -------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev_secret")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Initialize key store for provider API keys
key_store = ProviderKeyStore(get_encryption_secret())


def log(msg: str):
    """Sendet Logtext an das Frontend über Socket.IO."""
    socketio.emit("log", {"message": msg})


# -------------------------------------------------------------------
# Hilfsfunktionen
# -------------------------------------------------------------------
def to_datestr(x, include_time: bool = False) -> str:
    """
    Robuste Umwandlung in ISO format string.
    
    Args:
        x: Date/datetime/timestamp to convert
        include_time: If True, include time (for intraday). Otherwise just date.
        
    Returns:
        ISO format string (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
    """
    if isinstance(x, str):
        return x
    
    try:
        if include_time:
            return x.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return x.strftime("%Y-%m-%d")
    except Exception:
        try:
            dt = pd.to_datetime(x)
            if include_time:
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return dt.strftime("%Y-%m-%d")
        except Exception:
            return str(x)


# -------------------------------------------------------------------
# Provider Data Fetching with Caching
# -------------------------------------------------------------------
def get_market_data(
    provider_name: str,
    symbol: str,
    start: str,
    end: str,
    interval: str = "1d"
) -> pd.DataFrame:
    """
    Fetch market data using the specified provider with caching.
    
    Args:
        provider_name: Provider key ('yahoo', 'alpha_vantage', 'finnhub', 'tiingo')
        symbol: Stock symbol
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
        interval: Data interval ('1d', '1m', '5m', '15m', '30m', '60m')
    
    Returns:
        DataFrame with OHLCV data
    """
    # Check cache first (for intraday to reduce API calls)
    cache_key = get_cache_key(provider_name, symbol, start, end, interval)
    cached_data = market_data_cache.get(cache_key)
    if cached_data is not None:
        log(f"📦 Verwende gecachte Daten für {symbol}")
        return cached_data
    
    # Get API key if needed
    api_key = key_store.get_key(provider_name)
    
    # Get provider instance
    try:
        provider = get_provider(provider_name, api_key)
        log(f"📡 Lade Daten von {provider.get_provider_name()} für {symbol} ({interval}) ...")
        
        # Fetch data
        df = provider.get_ohlcv(symbol, start, end, interval)
        
        # Cache the result (especially useful for intraday)
        if interval != "1d":
            market_data_cache.set(cache_key, df, ttl=60)  # 60 second TTL for intraday
        
        return df
        
    except PermissionError as e:
        raise TickerDataError(
            f"API-Schlüssel fehlt oder ungültig für {provider_name}: {str(e)}"
        )
    except ConnectionError as e:
        raise TickerDataError(
            f"Verbindungsfehler oder Rate-Limit erreicht: {str(e)}"
        )
    except ValueError as e:
        raise TickerDataError(str(e))
    except Exception as e:
        raise TickerDataError(f"Fehler beim Laden der Daten: {str(e)}")


def download_data(symbol: str, start: str, end: str, provider_name: str = "yahoo", interval: str = "1d") -> pd.DataFrame:
    """
    Legacy function for backward compatibility. Now uses provider abstraction.
    Returns DataFrame with 'close' column for daily data, or full OHLCV for intraday.
    """
    if not start or not end:
        today = datetime.today().date()
        default_start = today - timedelta(days=365 * 2)
        if not start:
            start = default_start.isoformat()
        if not end:
            end = today.isoformat()

    df = get_market_data(provider_name, symbol, start, end, interval)
    
    if df.empty:
        raise TickerDataError(
            f"Keine Kursdaten für Symbol '{symbol}' gefunden. "
            f"Mögliche Ursachen: Das Symbol ist ungültig, wurde delisted, "
            f"oder es liegen keine Daten für den angegebenen Zeitraum vor."
        )
    
    # For backward compatibility with daily mode, return just close if requested
    if interval == "1d" and "close" in df.columns:
        return df[["close"]]
    
    return df


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Fügt technische Indikatoren hinzu."""
    df = df.copy()

    df["sma20"] = df["close"].rolling(20).mean()
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    roll_up = gain.rolling(14).mean()
    roll_down = loss.rolling(14).mean()
    rs = roll_up / roll_down
    df["rsi14"] = 100 - (100 / (1 + rs))

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    sma20 = df["close"].rolling(20).mean()
    std20 = df["close"].rolling(20).std()
    df["bb_upper"] = sma20 + 2 * std20
    df["bb_lower"] = sma20 - 2 * std20

    return df


def add_intraday_features(df: pd.DataFrame, interval: str = "5m") -> pd.DataFrame:
    """
    Add rich features for intraday modeling.
    
    Features include:
    - Returns (simple and log)
    - Volatility (rolling std)
    - ATR (Average True Range)
    - RSI
    - MACD
    - Bollinger Bands
    - VWAP (if volume available)
    - Momentum
    - Rolling highs/lows
    - Time-of-day encodings
    - Day-of-week encodings
    
    Args:
        df: DataFrame with OHLCV columns
        interval: Interval string for context
        
    Returns:
        DataFrame with added feature columns
    """
    df = df.copy()
    
    # Basic price features
    df['returns'] = df['close'].pct_change()
    df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
    
    # Volatility (rolling std of returns)
    df['volatility_10'] = df['returns'].rolling(10).std()
    df['volatility_30'] = df['returns'].rolling(30).std()
    
    # ATR (Average True Range)
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift(1))
    low_close = np.abs(df['low'] - df['close'].shift(1))
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr_14'] = true_range.rolling(14).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_diff'] = df['macd'] - df['macd_signal']
    
    # Bollinger Bands
    sma20 = df['close'].rolling(20).mean()
    std20 = df['close'].rolling(20).std()
    df['bb_upper'] = sma20 + 2 * std20
    df['bb_lower'] = sma20 - 2 * std20
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / sma20
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    # VWAP (Volume-Weighted Average Price) - only if volume is meaningful
    if 'volume' in df.columns and df['volume'].sum() > 0:
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        df['vwap_distance'] = (df['close'] - df['vwap']) / df['vwap']
    else:
        df['vwap'] = df['close']
        df['vwap_distance'] = 0
    
    # Momentum
    df['momentum_5'] = df['close'] - df['close'].shift(5)
    df['momentum_10'] = df['close'] - df['close'].shift(10)
    df['momentum_20'] = df['close'] - df['close'].shift(20)
    
    # Rolling highs/lows
    df['high_10'] = df['high'].rolling(10).max()
    df['low_10'] = df['low'].rolling(10).min()
    df['high_30'] = df['high'].rolling(30).max()
    df['low_30'] = df['low'].rolling(30).min()
    
    # Time-based features (cyclical encoding for better ML performance)
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute
    df['day_of_week'] = df.index.dayofweek
    
    # Cyclical encoding for time
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    
    return df


# -------------------------------------------------------------------
# Unterstützungs- & Widerstandsniveaus (Segment)
# -------------------------------------------------------------------
def compute_support_resistance(df_seg: pd.DataFrame, window: int = 5, n_levels: int = 3):
    prices = df_seg["close"]
    supports = []
    resistances = []

    if len(prices) < 2 * window + 1:
        return [], []

    values = prices.values

    for i in range(window, len(values) - window):
        window_slice = values[i - window : i + window + 1]
        price = values[i]
        if price == window_slice.min():
            supports.append(price)
        if price == window_slice.max():
            resistances.append(price)

    def cluster_levels(levels):
        if not levels:
            return []
        buckets = {}
        for p in levels:
            key = round(float(p), 2)
            buckets[key] = buckets.get(key, 0) + 1
        sorted_levels = sorted(buckets.items(), key=lambda x: x[1], reverse=True)
        return [lev for lev, _ in sorted_levels[:n_levels]]

    support_levels = cluster_levels(supports)
    resistance_levels = cluster_levels(resistances)

    return support_levels, resistance_levels


# -------------------------------------------------------------------
# Lineare Trendlinie über letztes Segment + Prognose
# -------------------------------------------------------------------
def compute_trendline(df_seg: pd.DataFrame, forecast_list, min_points: int = 20):
    prices = df_seg["close"].astype(float)
    n = len(prices)

    if n < min_points:
        return [], []

    x_hist = np.arange(n)
    y_hist = prices.to_numpy(dtype=float)

    slope, intercept = np.polyfit(x_hist, y_hist, 1)

    trend_hist = []
    for i, (idx, _) in enumerate(prices.items()):
        y = slope * i + intercept
        trend_hist.append({"date": to_datestr(idx), "value": float(y)})

    trend_forecast = []
    for j, (dt, _) in enumerate(forecast_list, start=1):
        x = n - 1 + j
        y = slope * x + intercept
        trend_forecast.append({"date": to_datestr(dt), "value": float(y)})

    return trend_hist, trend_forecast


# -------------------------------------------------------------------
# Features & Modell
# -------------------------------------------------------------------
def make_features(df: pd.DataFrame, n_lags: int = 20, use_intraday: bool = False):
    """
    Create supervised learning features for time series prediction.
    
    For daily mode: Uses simple lag features of close prices.
    For intraday mode: Uses rich feature set including indicators.
    
    Args:
        df: DataFrame with price data and indicators
        n_lags: Number of lag periods to use
        use_intraday: Whether to use rich intraday features
        
    Returns:
        X (features), y (targets)
    """
    if not use_intraday:
        # Legacy daily mode: simple lag features
        prices = df["close"].to_numpy(dtype=float).flatten()

        X, y = [], []
        for i in range(n_lags, len(prices)):
            X.append(prices[i - n_lags : i])
            y.append(prices[i])

        X = np.array(X)
        y = np.array(y).ravel()
        return X, y
    
    else:
        # Intraday mode: use rich features
        # Select feature columns (excluding target and non-numeric)
        feature_cols = [
            'open', 'high', 'low', 'close', 'volume',
            'returns', 'log_returns',
            'volatility_10', 'volatility_30',
            'atr_14', 'rsi_14',
            'macd', 'macd_signal', 'macd_diff',
            'bb_upper', 'bb_lower', 'bb_width', 'bb_position',
            'vwap_distance',
            'momentum_5', 'momentum_10', 'momentum_20',
            'high_10', 'low_10', 'high_30', 'low_30',
            'hour_sin', 'hour_cos', 'dow_sin', 'dow_cos'
        ]
        
        # Only use features that exist in df
        available_features = [col for col in feature_cols if col in df.columns]
        
        # Create lag features
        df_features = df[available_features].copy()
        df_features = df_features.dropna()
        
        X, y = [], []
        for i in range(n_lags, len(df_features)):
            # Flatten the lag window into a single feature vector
            lag_window = df_features.iloc[i - n_lags : i].values.flatten()
            X.append(lag_window)
            # Predict next close price
            y.append(df_features['close'].iloc[i])
        
        X = np.array(X)
        y = np.array(y).ravel()
        
        return X, y


def train_model(X: np.ndarray, y: np.ndarray, use_intraday: bool = False):
    """
    Train a regression model with time-series cross-validation.
    
    For intraday: Uses HistGradientBoostingRegressor (faster, better for many features)
    For daily: Uses RandomForest (legacy behavior)
    
    Args:
        X: Feature matrix
        y: Target values
        use_intraday: Whether this is intraday modeling
        
    Returns:
        Trained model
    """
    if use_intraday:
        log("Trainiere HistGradientBoosting-Modell (optimiert für Intraday) ...")
        # HistGradientBoostingRegressor is faster and handles many features better
        # It's also more robust to outliers and missing values
        model = HistGradientBoostingRegressor(
            max_iter=100,
            max_depth=8,
            learning_rate=0.05,
            random_state=42,
        )
        
        # Use TimeSeriesSplit for validation (no shuffling, respects time order)
        tscv = TimeSeriesSplit(n_splits=3)
        
        # Train on full dataset (already validated the approach)
        model.fit(X, y)
        
        # Log validation info
        scores = []
        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            temp_model = HistGradientBoostingRegressor(
                max_iter=100,
                max_depth=8,
                learning_rate=0.05,
                random_state=42,
            )
            temp_model.fit(X_train, y_train)
            score = temp_model.score(X_val, y_val)
            scores.append(score)
        
        avg_score = np.mean(scores)
        log(f"TimeSeriesSplit Validierung R² Score: {avg_score:.4f}")
        
    else:
        log("Trainiere RandomForest-Modell ...")
        model = RandomForestRegressor(
            n_estimators=300,
            max_depth=10,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X, y)
    
    return model


# -------------------------------------------------------------------
# Simpler „Backtest“ auf Trainingsdaten
# -------------------------------------------------------------------
def evaluate_backtest(X: np.ndarray, y: np.ndarray, model, threshold: float = 0.01):
    if len(X) == 0:
        return {
            "n_trades": 0,
            "hit_rate": None,
            "avg_return": None,
            "threshold": threshold,
        }

    y_pred = model.predict(X)

    last_close = X[:, -1]
    true_ret = (y - last_close) / last_close
    pred_ret = (y_pred - last_close) / last_close

    positions = np.where(
        pred_ret > threshold,
        1,
        np.where(pred_ret < -threshold, -1, 0),
    )

    trade_mask = positions != 0
    n_trades = int(trade_mask.sum())

    if n_trades == 0:
        return {
            "n_trades": 0,
            "hit_rate": None,
            "avg_return": None,
            "threshold": threshold,
        }

    pnl = positions[trade_mask] * true_ret[trade_mask]
    hit_rate = float((pnl > 0).mean())
    avg_return = float(pnl.mean())

    return {
        "n_trades": n_trades,
        "hit_rate": hit_rate,
        "avg_return": avg_return,
        "threshold": threshold,
    }


# -------------------------------------------------------------------
# Rekursive Mehrschritt-Vorhersage
# -------------------------------------------------------------------
def recursive_forecast(last_prices, model, steps, n_lags, last_date, interval: str = "1d"):
    """
    Recursive multi-step forecast.
    
    Args:
        last_prices: Recent price history (for lag features)
        model: Trained model
        steps: Number of steps to forecast
        n_lags: Number of lags used in model
        last_date: Last date/time in the data
        interval: Data interval ('1d' for daily, '5m' etc for intraday)
        
    Returns:
        List of (datetime, prediction) tuples
    """
    last_prices = np.array(last_prices, dtype=float).flatten().tolist()
    preds = []
    cur_date = last_date

    # Determine time delta based on interval
    if interval == "1d":
        time_delta = timedelta(days=1)
    elif interval == "1m":
        time_delta = timedelta(minutes=1)
    elif interval == "5m":
        time_delta = timedelta(minutes=5)
    elif interval == "15m":
        time_delta = timedelta(minutes=15)
    elif interval == "30m":
        time_delta = timedelta(minutes=30)
    elif interval == "60m":
        time_delta = timedelta(minutes=60)
    else:
        time_delta = timedelta(days=1)  # fallback

    for _ in range(steps):
        x = np.array(last_prices[-n_lags:]).reshape(1, -1)
        pred = float(model.predict(x)[0])
        cur_date += time_delta
        preds.append((cur_date, pred))
        last_prices.append(pred)

    return preds


# -------------------------------------------------------------------
# Routes - Provider Management
# -------------------------------------------------------------------
@app.route("/api/providers", methods=["GET"])
def api_list_providers():
    """List all available providers and their metadata."""
    try:
        providers = list_providers()
        
        # Add info about which providers have keys stored
        stored_keys = key_store.list_providers_with_keys()
        
        for provider in providers:
            provider['has_key'] = provider['key'] in stored_keys
        
        return jsonify({
            "providers": providers,
            "current_provider": "yahoo"  # default
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/provider_key", methods=["POST"])
def api_set_provider_key():
    """Set or update API key for a provider."""
    try:
        data = request.get_json()
        provider = data.get("provider")
        api_key = data.get("api_key")
        
        if not provider:
            return jsonify({"error": "Provider name required"}), 400
        
        if not api_key:
            return jsonify({"error": "API key required"}), 400
        
        # Validate provider exists
        providers = list_providers()
        valid_providers = [p['key'] for p in providers]
        
        if provider not in valid_providers:
            return jsonify({
                "error": f"Unknown provider '{provider}'. Valid: {', '.join(valid_providers)}"
            }), 400
        
        # Store the key (will be encrypted)
        key_store.set_key(provider, api_key)
        
        return jsonify({
            "success": True,
            "message": f"API key for {provider} saved successfully"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/provider_key", methods=["DELETE"])
def api_delete_provider_key():
    """Delete API key for a provider."""
    try:
        data = request.get_json()
        provider = data.get("provider")
        
        if not provider:
            return jsonify({"error": "Provider name required"}), 400
        
        deleted = key_store.delete_key(provider)
        
        if deleted:
            return jsonify({
                "success": True,
                "message": f"API key for {provider} deleted"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"No API key found for {provider}"
            }), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------------
# Routes - Main App
# -------------------------------------------------------------------
@app.route("/")
def index():
    end_default = datetime.today().date()
    start_default = end_default - timedelta(days=365 * 2)
    return render_template(
        "index.html",
        default_symbol="AAPL",
        default_start=start_default.isoformat(),
        default_end=end_default.isoformat(),
    )


@app.route("/health")
def health():
    """Health check endpoint for deployment verification"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.getenv("APP_VERSION", "unknown")
    }), 200


@app.route("/api/train_predict", methods=["POST"])
def api_train_predict():
    p = request.get_json()
    symbol = (p.get("symbol") or "AAPL").upper()
    start = p.get("start")
    end = p.get("end")
    steps = int(p.get("steps") or 10)

    threshold_pct = float(p.get("threshold_pct") or 1.0)
    threshold = threshold_pct / 100.0
    segment_len_param = int(p.get("segment_len") or 120)
    horizon_days = int(p.get("horizon_days") or 1)
    
    # NEW: Provider and intraday support
    provider_name = p.get("provider") or "yahoo"
    interval = p.get("interval") or "1d"
    lookback_days = int(p.get("lookback_days") or 60)
    
    # Determine if this is intraday mode
    is_intraday = interval != "1d"

    try:
        # Adjust date range for intraday if needed
        if is_intraday and lookback_days:
            # For intraday, use lookback_days from end date
            if not end:
                end = datetime.today().date().isoformat()
            end_dt = datetime.fromisoformat(end)
            start_dt = end_dt - timedelta(days=lookback_days)
            start = start_dt.isoformat()
            log(f"Intraday-Modus: Verwende {lookback_days} Tage Lookback ({start} → {end})")
        
        # Fetch data with provider
        df = download_data(symbol, start, end, provider_name=provider_name, interval=interval)

        # Get symbol name and news (using Yahoo for now, as it's free)
        full_name = get_symbol_name(symbol, logger=log)
        quote, news_items = get_quote_and_news(symbol, logger=log)

        # Add indicators based on mode
        if is_intraday:
            log("Berechne Intraday-Indikatoren & Features ...")
            df = add_intraday_features(df, interval)
        else:
            log("Berechne Indikatoren ...")
            df = add_indicators(df)

        segment_len = min(segment_len_param, len(df))
        df_seg = df.iloc[-segment_len:]

        log("Berechne Unterstützungs- und Widerstandsniveaus ...")
        support_levels, resistance_levels = compute_support_resistance(df_seg)

        log("Erzeuge Features ...")
        n_lags = 20 if not is_intraday else 30  # More lags for intraday
        X, y = make_features(df, n_lags, use_intraday=is_intraday)

        if len(X) < 50:
            raise ValueError("Zu wenige Daten zum Trainieren (mind. 50 Samples).")

        model = train_model(X, y, use_intraday=is_intraday)

        backtest = evaluate_backtest(X, y, model, threshold=threshold)

        log("Erzeuge Vorhersage ...")
        last_prices = df["close"].to_numpy(dtype=float).flatten()
        last_date = df.index[-1]

        forecast = recursive_forecast(
            last_prices=last_prices,
            model=model,
            steps=steps,
            n_lags=n_lags,
            last_date=last_date,
            interval=interval,
        )

        if steps > 0:
            horizon_days = max(1, min(horizon_days, steps))
        else:
            horizon_days = 1

        close_series = df["close"].astype(float)

        # Format dates/timestamps based on mode
        include_time = is_intraday
        
        history = [
            {"date": to_datestr(idx, include_time), "close": float(val)}
            for idx, val in close_series.items()
        ]

        indicators = {}
        indicator_names = [
            "sma20",
            "ema20",
            "rsi14",
            "macd",
            "macd_signal",
            "bb_upper",
            "bb_lower",
        ]
        # For intraday, also include rsi_14 (with underscore)
        if is_intraday:
            indicator_names.extend(["rsi_14", "atr_14", "vwap_distance"])
        
        for name in indicator_names:
            if name in df.columns:
                col = df[name].astype(float).dropna()
                indicators[name] = [
                    {"date": to_datestr(idx, include_time), "value": float(v)}
                    for idx, v in col.items()
                ]

        forecast_out = [
            {"date": to_datestr(dt, include_time), "pred": float(val)} for dt, val in forecast
        ]

        trend_hist, trend_forecast = compute_trendline(df_seg, forecast)

        levels_start = df_seg.index[0]
        levels_end = forecast[-1][0] if forecast else df.index[-1]
        levels = {
            "supports": [float(x) for x in support_levels],
            "resistances": [float(x) for x in resistance_levels],
            "start_date": to_datestr(levels_start, include_time),
            "end_date": to_datestr(levels_end, include_time),
        }

        trend = {"hist": trend_hist, "forecast": trend_forecast}

        if forecast_out:
            last_close = float(close_series.iloc[-1])
            target_idx = min(horizon_days - 1, len(forecast_out) - 1)
            target_price = float(forecast_out[target_idx]["pred"])
            delta_pct = (target_price - last_close) / last_close
            sig_type = "neutral"
            if delta_pct > threshold:
                sig_type = "bullish"
            elif delta_pct < -threshold:
                sig_type = "bearish"
            signal = {
                "type": sig_type,
                "delta_pct": float(delta_pct),
                "last_close": last_close,
                "target_price": target_price,
                "horizon_days": horizon_days,
                "threshold": threshold,
                "threshold_pct": threshold_pct,
            }
        else:
            signal = {
                "type": "neutral",
                "delta_pct": 0.0,
                "last_close": float(close_series.iloc[-1]),
                "target_price": None,
                "horizon_days": horizon_days,
                "threshold": threshold,
                "threshold_pct": threshold_pct,
            }

        log("Fertig (Simulation).")

        return jsonify(
            {
                "symbol": symbol,
                "symbol_name": full_name,
                "history": history,
                "indicators": indicators,
                "forecast": forecast_out,
                "levels": levels,
                "trend": trend,
                "signal": signal,
                "backtest": backtest,
                "quote": quote,
                "news": news_items,
                "params": {
                    "threshold_pct": threshold_pct,
                    "segment_len": segment_len,
                    "horizon_days": horizon_days,
                },
            }
        )

    except TickerDataError as e:
        # Handle ticker-specific errors with helpful suggestions
        error_msg = str(e)
        log(f"Fehler: {error_msg}")
        suggestion = (
            f" Vorschläge: Versuchen Sie bekannte Symbole wie AAPL (Apple), "
            f"MSFT (Microsoft), GOOGL (Google), TSLA (Tesla), oder AMZN (Amazon)."
        )
        return jsonify({"error": error_msg + suggestion}), 400
    
    except Exception as e:
        # Handle other unexpected errors
        error_msg = str(e)
        log(f"Fehler: {error_msg}")
        return jsonify({"error": error_msg}), 400


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    socketio.run(app, host="0.0.0.0", port=port, debug=debug, allow_unsafe_werkzeug=True)
