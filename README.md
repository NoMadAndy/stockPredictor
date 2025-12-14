# Stock Predictor

Ein Web-basiertes Tool zur Aktienanalyse und -vorhersage mit Machine Learning.

## Funktionen

- **Kursdaten-Analyse**: Lädt historische Aktienkurse über yfinance
- **Technische Indikatoren**: Berechnet SMA, EMA, RSI, MACD und Bollinger Bands
- **ML-Vorhersage**: Nutzt Random Forest Regression für Kursprognosen
- **Unterstützungs-/Widerstandsniveaus**: Identifiziert wichtige Preisniveaus
- **Trendlinie**: Berechnet lineare Trends für historische und prognostizierte Daten
- **News-Integration**: Zeigt aktuelle Nachrichten zur Aktie (yfinance + NewsAPI)
- **Echtzeit-Updates**: WebSocket-Verbindung für Live-Logs

## Anforderungen

- Python 3.8+
- Alle Abhängigkeiten aus `requirements.txt`

## Installation

### Lokale Installation

```bash
# Repository klonen
git clone https://github.com/NoMadAndy/stockPredictor.git
cd stockPredictor

# Virtuelle Umgebung erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate  # Windows

# Abhängigkeiten installieren
pip install -r requirements.txt

# Server starten
python app.py
```

### Docker Installation

```bash
# Docker Image bauen
docker-compose build

# Container starten
docker-compose up -d

# Logs anzeigen
docker-compose logs -f
```

## Konfiguration

### Port-Konfiguration

Die Anwendung läuft standardmäßig auf Port 8001. Dies kann in der `docker-compose.yml` oder beim direkten Start angepasst werden.

### NewsAPI-Key (Optional)

Für erweiterte Nachrichten-Features:

1. Registrieren Sie sich bei [NewsAPI.org](https://newsapi.org/)
2. Erstellen Sie eine Datei `news_api_key.txt` im Projektverzeichnis
3. Fügen Sie Ihren API-Key in die Datei ein

Alternativ kann der Key auch über Umgebungsvariablen gesetzt werden:
```bash
export NEWSAPI_KEY="ihr-api-key"
# oder
export NEWSAPI_KEY_FILE="/pfad/zur/key-datei.txt"
```

### Secret Key

Für Produktionsumgebungen sollte ein sicherer Secret Key gesetzt werden:
```bash
export SECRET_KEY="ihr-sicherer-secret-key"
```

## Verwendung

1. Öffnen Sie `http://localhost:8001` im Browser
2. Geben Sie ein Aktiensymbol ein (z.B. "DAC", "AAPL")
3. Wählen Sie den Zeitraum für die Analyse
4. Passen Sie die Parameter an:
   - **Vorhersageschritte**: Anzahl der Tage in die Zukunft
   - **Schwellenwert**: Prozentsatz für Handelssignale
   - **Segmentlänge**: Anzahl der Tage für Support/Resistance
   - **Horizont**: Tage für Signalberechnung
5. Klicken Sie auf "Analyse starten"

## API-Endpoints

### POST /api/train_predict

Führt eine vollständige Analyse und Vorhersage durch.

**Request Body:**
```json
{
  "symbol": "DAC",
  "start": "2023-01-01",
  "end": "2024-12-31",
  "steps": 10,
  "threshold_pct": 1.0,
  "segment_len": 120,
  "horizon_days": 1
}
```

**Response:**
```json
{
  "symbol": "DAC",
  "symbol_name": "Danaos Corporation",
  "history": [...],
  "indicators": {...},
  "forecast": [...],
  "levels": {...},
  "trend": {...},
  "signal": {...},
  "backtest": {...},
  "quote": {...},
  "news": [...]
}
```

## Architektur

- **Backend**: Flask mit Socket.IO für Echtzeit-Kommunikation
- **ML-Modell**: RandomForestRegressor von scikit-learn
- **Datenbeschaffung**: yfinance für Aktiendaten, NewsAPI für Nachrichten
- **Frontend**: HTML/JavaScript mit Chart.js für Visualisierungen

## Auto-Deployment

Das Repository ist für automatisches Deployment konfiguriert:

1. **GitHub Webhook**: Bei Push-Events wird automatisch neu deployed
2. **Systemd Service**: Automatischer Start beim Serverstart
3. **Port 8001**: Standardport für die Anwendung

Details zur Deployment-Konfiguration siehe `deploy.sh` und `stockpredictor.service`.

## Entwicklung

### Tests ausführen

```bash
# Falls Tests vorhanden sind
python -m pytest tests/
```

### Linting

```bash
# Code-Qualität prüfen
flake8 app.py news_service.py
```

## Lizenz

Siehe LICENSE-Datei im Repository.

## Support

Bei Fragen oder Problemen öffnen Sie bitte ein Issue im GitHub-Repository.
