# Changelog

Alle bemerkenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt hält sich an [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### Hinzugefügt
- **Multi-Provider-Architektur**:
  - Abstrakte Provider-Schnittstelle (`providers/base.py`)
  - Yahoo Finance Provider (yfinance, kostenlos)
  - Alpha Vantage Provider (API-Key erforderlich)
  - Finnhub Provider (API-Key erforderlich)
  - Tiingo Provider (API-Key erforderlich)
  - Provider-Factory für einfachen Wechsel zwischen Anbietern

- **Sichere API-Key-Verwaltung**:
  - Verschlüsselte Speicherung mit Fernet (symmetrische Verschlüsselung)
  - Schlüssel-Ableitung von `API_KEY_ENCRYPTION_SECRET` oder `SECRET_KEY`
  - REST-API-Endpoints:
    - `GET /api/providers` - Liste aller Anbieter
    - `POST /api/provider_key` - Speichern von API-Schlüsseln
    - `DELETE /api/provider_key` - Löschen von API-Schlüsseln
  - Persistenz in `config/provider_keys.json` (verschlüsselt)

- **Intraday-Unterstützung**:
  - Intervalle: 1m, 5m, 15m, 30m, 60m (anbieterabhängig)
  - Erweiterte Feature-Engineering für Intraday:
    - Returns & Log-Returns
    - Volatilität (Rolling Std)
    - ATR (Average True Range)
    - RSI, MACD, Bollinger Bands
    - VWAP (Volume-Weighted Average Price)
    - Momentum-Indikatoren
    - Rolling Highs/Lows
    - Zeitbasierte Features (Stunde, Wochentag mit zyklischer Kodierung)
  - HistGradientBoostingRegressor für Intraday (schneller, besser für viele Features)
  - TimeSeriesSplit für zeitreihengerechte Validierung
  - Intraday-Timestamp-Formatierung (YYYY-MM-DD HH:MM:SS)
  - Lookback-Parameter für flexible Historie

- **Caching-Layer**:
  - In-Memory-Cache mit TTL (Time-To-Live)
  - 60-Sekunden-Cache für Intraday-Daten
  - Reduziert API-Aufrufe und schont Rate Limits
  - Thread-sicheres Design

- **Frontend-Erweiterungen**:
  - Dropdown zur Provider-Auswahl
  - API-Key-Eingabefeld mit Hinweisen
  - Intervall-Auswahl (täglich/intraday)
  - Lookback-Tage für Intraday
  - LocalStorage-Persistenz für Provider-Einstellungen
  - Automatisches Laden gespeicherter API-Keys
  - Kontextabhängige Hilfe-Texte

### Geändert
- `/api/train_predict` erweitert um Parameter:
  - `provider`: Auswahl des Datenanbieters
  - `interval`: Datenintervall (1d, 5m, etc.)
  - `lookback_days`: Historie für Intraday
- Modell-Training:
  - Täglich: RandomForestRegressor (wie bisher)
  - Intraday: HistGradientBoostingRegressor (optimiert)
  - TimeSeriesSplit-Validierung für Intraday
- Feature-Erstellung:
  - Täglich: Einfache Lag-Features (Rückwärtskompatibel)
  - Intraday: Umfangreiche technische und zeitbasierte Features
- Forecast-Zeitstempel:
  - Täglich: YYYY-MM-DD
  - Intraday: YYYY-MM-DD HH:MM:SS

### Sicherheit
- Verschlüsselte Speicherung von API-Schlüsseln
- Separater Verschlüsselungs-Secret (`API_KEY_ENCRYPTION_SECRET`)
- Warnung bei Verwendung von Default-Secrets
- `.gitignore` erweitert um `provider_keys.json`

### Abhängigkeiten
- `cryptography==41.0.7` für Fernet-Verschlüsselung
- Technische Indikatoren manuell implementiert (kein externes TA-Library erforderlich)

### Dokumentation
- README erweitert mit:
  - Provider-Beschreibungen und Anmeldungs-Links
  - API-Key-Verwaltungs-Anleitung
  - Intraday-Modus-Erklärung
  - Rate-Limit-Hinweise
  - Sicherheits-Konfiguration für Verschlüsselung
- CHANGELOG aktualisiert mit allen Änderungen

## [1.1.0] - 2024-12-14

### Hinzugefügt
- **Auto-Deployment-Infrastruktur**:
  - Docker und Docker Compose Support für containerisierte Deployment
  - Dockerfile mit optimiertem Python 3.11 Image
  - docker-compose.yml für einfache Orchestrierung
  - Systemd Service-Dateien (stockpredictor.service, webhook-receiver.service)
  - Deployment-Skript (deploy.sh) für automatische Aktualisierung
  - GitHub Webhook-Receiver (webhook_receiver.py) für Push-Events
  - Interaktiver Setup-Assistent (setup.sh)

- **Dokumentation**:
  - Umfassende README.md mit Nutzungsanleitung und API-Dokumentation
  - Detaillierte INSTALLATION.md für verschiedene Deployment-Szenarien
  - CHANGELOG.md nach Keep a Changelog Standard
  - Sicherheitshinweise für Produktions-Deployment

- **Konfiguration**:
  - requirements.txt für vollständiges Dependency Management
  - .gitignore für Python-Projekte
  - Umgebungsvariablen-Support für flexible Konfiguration
  - Sicherheitswarnungen für Default-Secrets

### Geändert
- Port von 5000 auf 8001 geändert (mit Umgebungsvariablen-Unterstützung)
- app.py für Produktionsumgebung optimiert
- Konfiguration über PORT, SECRET_KEY und DEBUG Umgebungsvariablen
- Debug-Modus standardmäßig deaktiviert in Produktion

### Sicherheit
- Klare Warnungen für unsichere Default-Secrets
- Anleitung zur Secret-Generierung mit openssl
- Root-User-Warnung für Webhook-Receiver mit Erklärung
- Automatische Secret-Generierung in Installationsanleitung

## [1.0.0] - 2024-12-14

### Hinzugefügt
- Initiale Version der Stock Predictor Anwendung
- Flask Web-Server mit Socket.IO Integration
- RandomForest ML-Modell für Aktienvorhersagen
- Technische Indikatoren (SMA, EMA, RSI, MACD, Bollinger Bands)
- Unterstützungs- und Widerstandsniveau-Berechnung
- Trendlinien-Analyse
- Integration mit yfinance für Aktien- und News-Daten
- NewsAPI.org Integration für erweiterte Nachrichten
- Echtzeit-Logging über WebSockets
- Backtest-Funktionalität für Modellbewertung
- Responsive Web-Interface
- Symbol-Name-Auflösung
- Kombinierte News-Feeds (yfinance + NewsAPI)
- Deduplizierung von News-Artikeln
- Robuste API-Key-Verwaltung für NewsAPI

### Technische Details
- Python Flask Backend
- scikit-learn für Machine Learning
- pandas/numpy für Datenverarbeitung
- yfinance für Finanzdaten
- Socket.IO für Echtzeit-Kommunikation
