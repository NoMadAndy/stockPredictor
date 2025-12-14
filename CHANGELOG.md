# Changelog

Alle bemerkenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt hält sich an [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

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
