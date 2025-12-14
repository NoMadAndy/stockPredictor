import os
from datetime import datetime, timedelta

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor

from news_service import get_symbol_name, get_quote_and_news  # <--- NEU

# -------------------------------------------------------------------
# Flask + Socket.IO Setup
# -------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev_secret")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


def log(msg: str):
    """Sendet Logtext an das Frontend über Socket.IO."""
    socketio.emit("log", {"message": msg})


# -------------------------------------------------------------------
# Hilfsfunktionen
# -------------------------------------------------------------------
def to_datestr(x) -> str:
    """Robuste Umwandlung in YYYY-MM-DD, egal ob Timestamp, datetime oder String."""
    if isinstance(x, str):
        return x
    try:
        return x.strftime("%Y-%m-%d")
    except Exception:
        try:
            return pd.to_datetime(x).strftime("%Y-%m-%d")
        except Exception:
            return str(x)


# -------------------------------------------------------------------
# Datenbeschaffung & Indikatoren
# -------------------------------------------------------------------
def download_data(symbol: str, start: str, end: str) -> pd.DataFrame:
    """
    Lädt Kursdaten mit yfinance und gibt ein DataFrame mit GENAU EINER
    Float-Spalte 'close' zurück. Behandelt auch MultiIndex-Spalten.
    """
    if not start or not end:
        today = datetime.today().date()
        default_start = today - timedelta(days=365 * 2)
        if not start:
            start = default_start.isoformat()
        if not end:
            end = today.isoformat()

    log(f"Lade Kursdaten für {symbol} {start} → {end} ...")

    df = yf.download(symbol, start=start, end=end, progress=False)

    if df is None or df.empty:
        raise ValueError(
            f"Keine Kursdaten für Symbol '{symbol}' gefunden. "
            f"Mögliche Ursachen: Das Symbol ist ungültig, wurde delisted, "
            f"oder es liegen keine Daten für den angegebenen Zeitraum vor. "
            f"Bitte überprüfen Sie das Tickersymbol und versuchen Sie es erneut."
        )

    if isinstance(df.columns, pd.MultiIndex):
        try:
            close_series = df[("Close", symbol)]
        except Exception:
            try:
                closes = df.xs("Close", level=0, axis=1)
                if symbol in closes.columns:
                    close_series = closes[symbol]
                else:
                    close_series = closes.iloc[:, 0]
            except Exception:
                close_series = df.iloc[:, 0]
    else:
        if "Close" in df.columns:
            close_series = df["Close"]
        elif "Adj Close" in df.columns:
            close_series = df["Adj Close"]
        elif df.shape[1] == 1:
            close_series = df.iloc[:, 0]
        else:
            raise ValueError("Konnte keine Schlusskurs-Spalte finden (Close/Adj Close).")

    close_series = pd.Series(close_series, index=df.index).astype(float)
    close_series = close_series.dropna()

    if close_series.empty:
        raise ValueError("Schlusskurs-Serie ist leer nach Bereinigung.")

    out = close_series.to_frame(name="close")
    out.index = pd.to_datetime(out.index)
    out.sort_index(inplace=True)

    return out


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
def make_features(df: pd.DataFrame, n_lags: int = 20):
    prices = df["close"].to_numpy(dtype=float).flatten()

    X, y = [], []
    for i in range(n_lags, len(prices)):
        X.append(prices[i - n_lags : i])
        y.append(prices[i])

    X = np.array(X)
    y = np.array(y).ravel()
    return X, y


def train_model(X: np.ndarray, y: np.ndarray) -> RandomForestRegressor:
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
def recursive_forecast(last_prices, model, steps, n_lags, last_date):
    last_prices = np.array(last_prices, dtype=float).flatten().tolist()
    preds = []
    cur_date = last_date

    for _ in range(steps):
        x = np.array(last_prices[-n_lags:]).reshape(1, -1)
        pred = float(model.predict(x)[0])
        cur_date += timedelta(days=1)
        preds.append((cur_date, pred))
        last_prices.append(pred)

    return preds


# -------------------------------------------------------------------
# Routes
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

    try:
        df = download_data(symbol, start, end)

        full_name = get_symbol_name(symbol, logger=log)
        quote, news_items = get_quote_and_news(symbol, logger=log)

        log("Berechne Indikatoren ...")
        df = add_indicators(df)

        segment_len = min(segment_len_param, len(df))
        df_seg = df.iloc[-segment_len:]

        log("Berechne Unterstützungs- und Widerstandsniveaus ...")
        support_levels, resistance_levels = compute_support_resistance(df_seg)

        log("Erzeuge Features ...")
        n_lags = 20
        X, y = make_features(df, n_lags)

        if len(X) < 50:
            raise ValueError("Zu wenige Daten zum Trainieren (mind. 50 Samples).")

        model = train_model(X, y)

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
        )

        if steps > 0:
            horizon_days = max(1, min(horizon_days, steps))
        else:
            horizon_days = 1

        close_series = df["close"].astype(float)

        history = [
            {"date": to_datestr(idx), "close": float(val)}
            for idx, val in close_series.items()
        ]

        indicators = {}
        for name in [
            "sma20",
            "ema20",
            "rsi14",
            "macd",
            "macd_signal",
            "bb_upper",
            "bb_lower",
        ]:
            if name in df.columns:
                col = df[name].astype(float).dropna()
                indicators[name] = [
                    {"date": to_datestr(idx), "value": float(v)}
                    for idx, v in col.items()
                ]

        forecast_out = [
            {"date": to_datestr(dt), "pred": float(val)} for dt, val in forecast
        ]

        trend_hist, trend_forecast = compute_trendline(df_seg, forecast)

        levels_start = df_seg.index[0]
        levels_end = forecast[-1][0] if forecast else df.index[-1]
        levels = {
            "supports": [float(x) for x in support_levels],
            "resistances": [float(x) for x in resistance_levels],
            "start_date": to_datestr(levels_start),
            "end_date": to_datestr(levels_end),
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

    except Exception as e:
        error_msg = str(e)
        log(f"Fehler: {error_msg}")
        
        # Provide helpful suggestions for common errors
        if "Keine Kursdaten" in error_msg or "delisted" in error_msg.lower():
            suggestion = (
                f" Vorschläge: Versuchen Sie bekannte Symbole wie AAPL (Apple), "
                f"MSFT (Microsoft), GOOGL (Google), TSLA (Tesla), oder AMZN (Amazon)."
            )
            error_msg = error_msg + suggestion
        
        return jsonify({"error": error_msg}), 400


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    socketio.run(app, host="0.0.0.0", port=port, debug=debug, allow_unsafe_werkzeug=True)
