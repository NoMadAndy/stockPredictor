# Changelog

Alle bemerkenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt hält sich an [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### Hinzugefügt
- Auto-Deployment-Konfiguration mit GitHub Webhooks
- Docker und Docker Compose Support
- Systemd Service-Datei für automatischen Start
- Deployment-Skript für automatische Aktualisierung
- Webhook-Receiver für GitHub-Integration
- Umfassende README.md Dokumentation
- requirements.txt für Dependency Management
- .gitignore für Python-Projekte

### Geändert
- Port von 5000 auf 8001 geändert
- Konfiguration für Produktionsumgebung optimiert

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
