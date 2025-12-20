# Stock Predictor

Ein Web-basiertes Tool zur Aktienanalyse und -vorhersage mit Machine Learning.

## Funktionen

- **Multi-Provider-Unterstützung**: Wählen Sie zwischen Yahoo Finance, Alpha Vantage, Finnhub und Tiingo
- **Intraday-Analyse**: Vorhersagen auf 1-Minuten- bis Stunden-Intervallen mit erweiterten Features
- **Technische Indikatoren**: 
  - Täglich: SMA, EMA, RSI, MACD, Bollinger Bands
  - Intraday: ATR, VWAP, Volatilität, Momentum, zeitbasierte Features
- **ML-Vorhersage**: 
  - Täglich: Random Forest Regression
  - Intraday: Histogram Gradient Boosting mit TimeSeriesSplit-Validierung
- **Sichere API-Key-Verwaltung**: Verschlüsselte Speicherung mit Fernet (cryptography)
- **Caching**: In-Memory-Cache mit TTL für Intraday-Daten (reduziert API-Aufrufe)
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

# Verify imports (optional)
python -c "import app; import news_service; import utils; print('✓ All imports successful')"
```

### Docker Installation

```bash
# Docker Image bauen
docker-compose build

# Container starten
docker-compose up -d

# Logs anzeigen
docker-compose logs -f

# Verify installation (optional)
docker-compose exec app python -c "import app; import news_service; import utils; print('✓ All imports successful')"
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

### Marktdaten-Provider und API-Schlüssel

Die Anwendung unterstützt mehrere Datenanbieter:

#### Yahoo Finance (Standard, kostenlos)
- Keine Registrierung erforderlich
- Unterstützt täglich und Intraday (begrenzt auf ~60 Tage History)
- Auswahl in der UI: "Yahoo Finance"

#### Alpha Vantage
1. Kostenlosen API-Key unter https://www.alphavantage.co/support/#api-key holen
2. In der Web-UI unter "API-Schlüssel" eingeben
3. Rate Limits: 5 Aufrufe/Minute, 100 Aufrufe/Tag (kostenlose Stufe)
4. Intraday-Daten auf ~30 Tage begrenzt

#### Finnhub
1. Kostenlosen API-Key unter https://finnhub.io/register holen
2. In der Web-UI unter "API-Schlüssel" eingeben
3. Rate Limits: 60 Aufrufe/Minute (kostenlose Stufe)
4. Intraday-Daten erfordern Premium-Abonnement

#### Tiingo
1. Kostenlosen API-Key unter https://www.tiingo.com/account/api/token holen
2. In der Web-UI unter "API-Schlüssel" eingeben
3. Unterstützt US-Aktien für Intraday (IEX)
4. Gute kostenlose Stufe mit angemessenen Limits

**API-Key-Speicherung**: API-Schlüssel werden verschlüsselt auf dem Server gespeichert (Fernet-Verschlüsselung) und bleiben nach Neuladen der Seite erhalten.

### Secret Key (Erforderlich für Produktion!)

**WICHTIG**: Für Produktionsumgebungen **muss** ein sicherer Secret Key gesetzt werden!

```bash
# Secret Key für verschlüsselte API-Key-Speicherung generieren
API_KEY_ENCRYPTION_SECRET=$(openssl rand -hex 32)
export API_KEY_ENCRYPTION_SECRET="$API_KEY_ENCRYPTION_SECRET"

# Flask Secret Key (getrennt vom Encryption Secret)
SECRET_KEY=$(openssl rand -hex 32)
export SECRET_KEY="$SECRET_KEY"

# Oder in docker-compose.yml eintragen
# Oder in der systemd Service-Datei konfigurieren
```

⚠️ **Sicherheitshinweis**: 
- Die Standard-Secrets sind **nicht sicher** und müssen vor dem Deployment geändert werden!
- `API_KEY_ENCRYPTION_SECRET` wird für die Verschlüsselung der Provider-API-Schlüssel verwendet
- `SECRET_KEY` wird für Flask-Sessions und als Fallback für die Verschlüsselung verwendet
- Siehe INSTALLATION.md für Details.

## Verwendung

1. Öffnen Sie `http://localhost:8001` im Browser
2. Wählen Sie einen **Datenanbieter** aus (Yahoo Finance ist Standard)
3. Falls erforderlich, geben Sie Ihren **API-Schlüssel** ein (wird automatisch gespeichert)
4. Geben Sie ein **Aktiensymbol** ein (z.B. "AAPL", "MSFT", "GOOGL")
5. Wählen Sie das **Intervall**:
   - **Täglich (1d)**: Für längerfristige Analysen (Jahre)
   - **Intraday (60m, 30m, 15m, 5m, 1m)**: Für kurzfristige Analysen (Tage bis Wochen)
6. Bei Intraday: Setzen Sie **Lookback-Tage** (wie viele Tage zurück geladen werden sollen)
7. Wählen Sie den Zeitraum (für tägliche Daten)
8. Passen Sie weitere Parameter an:
   - **Vorhersageschritte**: Anzahl der Perioden in die Zukunft
   - **Schwellenwert**: Prozentsatz für Handelssignale
   - **Segmentlänge**: Anzahl der Kerzen für Support/Resistance
   - **Horizont**: Perioden für Signalberechnung
9. Klicken Sie auf "Trainieren & Vorhersagen"

### Intraday-Modus Hinweise

- **Yahoo Finance**: Intraday-Daten auf ~60 Tage beschränkt
- **Alpha Vantage**: Intraday-Daten auf ~30 Tage beschränkt, Rate Limits beachten
- **Finnhub**: Premium-Abonnement für Intraday erforderlich
- **Tiingo**: Funktioniert gut für US-Aktien (IEX-Daten)
- **Caching**: Intraday-Daten werden 60 Sekunden gecacht, um API-Limits zu schonen
- **Empfehlung**: Für Intraday 7-30 Tage Lookback verwenden

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

## Auto-Deployment & CI/CD

Das Repository verfügt über eine vollständige CI/CD-Pipeline für automatisierte Deployments:

### Funktionen

1. **Continuous Integration**
   - Automatische Tests bei jedem Push
   - Docker Image Build und Verifikation
   - Code-Qualitätsprüfungen

2. **Preprod Deployment** 
   - Automatisch bei Push zu `main` Branch
   - Webhook-basierte Deployment-Trigger
   - Automatische Health Checks

3. **Production Deployment**
   - Release-basiert mit manuellem Approval
   - Automatisches Backup und Rollback
   - Erweiterte Health Checks und Validierung

4. **Deployment-Infrastruktur**
   - GitHub Actions Workflows
   - Webhook Receiver Service
   - Systemd Service Management
   - Nginx Reverse Proxy

### Quick Start

**Preprod Server installieren:**
```bash
sudo wget https://raw.githubusercontent.com/NoMadAndy/stockPredictor/main/install-server.sh
sudo ./install-server.sh preprod
```

**Production Server installieren:**
```bash
sudo ./install-server.sh production
```

**Deployment auslösen:**
```bash
# Preprod: Einfach zu main pushen
git push origin main

# Production: Release erstellen
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0
# Dann auf GitHub: Create Release
```

### Dokumentation

📖 **Vollständige Anleitung**: Siehe [DEPLOYMENT.md](DEPLOYMENT.md) für:
- Detaillierte Installationsanleitung
- GitHub Actions Setup
- Webhook-Konfiguration
- Monitoring und Troubleshooting
- Sicherheits-Best Practices
- Rollback-Verfahren

**Kurz-Dokumentation**: Siehe [INSTALLATION.md](INSTALLATION.md) für manuelle Setup-Optionen.

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
