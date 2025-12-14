# Stock Predictor - Schnellstart

Diese Anleitung zeigt die schnellste Methode, um Stock Predictor zu installieren und zu starten.

## Docker-Methode (Empfohlen - 2 Minuten)

```bash
# 1. Repository klonen
git clone https://github.com/NoMadAndy/stockPredictor.git
cd stockPredictor

# 2. Optional: NewsAPI Key konfigurieren
echo "YOUR_NEWS_API_KEY" > news_api_key.txt

# 3. Starten!
docker-compose up -d

# 4. Überprüfen
docker-compose logs -f
```

Die Anwendung läuft auf: **http://localhost:8001**

## Interaktiver Setup (5 Minuten)

```bash
# 1. Repository klonen
git clone https://github.com/NoMadAndy/stockPredictor.git
cd stockPredictor

# 2. Setup-Assistent ausführen
sudo bash setup.sh
```

Der Setup-Assistent führt Sie durch die Installation.

## Lokale Entwicklung (3 Minuten)

```bash
# 1. Repository klonen
git clone https://github.com/NoMadAndy/stockPredictor.git
cd stockPredictor

# 2. Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate

# 3. Abhängigkeiten installieren
pip install -r requirements.txt

# 4. Server starten
python app.py
```

Die Anwendung läuft auf: **http://localhost:8001**

## Auto-Deployment einrichten (15 Minuten)

Für automatische Updates bei GitHub Push-Events:

```bash
# 1. Webhook Receiver installieren
sudo cp webhook-receiver.service /etc/systemd/system/
WEBHOOK_SECRET=$(openssl rand -hex 32)
sudo sed -i "s/PLEASE_CHANGE_THIS_WEBHOOK_SECRET_IN_PRODUCTION/${WEBHOOK_SECRET}/" \
    /etc/systemd/system/webhook-receiver.service
sudo systemctl enable webhook-receiver
sudo systemctl start webhook-receiver

# 2. GitHub Webhook konfigurieren
# Gehen Sie zu: https://github.com/NoMadAndy/stockPredictor/settings/hooks
# - Payload URL: http://ihr-server:9001/webhook
# - Content type: application/json
# - Secret: <das generierte WEBHOOK_SECRET>
# - Events: Just the push event
```

Jetzt wird die Anwendung automatisch aktualisiert, wenn Sie Code zu GitHub pushen!

## Nützliche Befehle

### Docker
```bash
docker-compose ps              # Status anzeigen
docker-compose logs -f         # Logs anzeigen
docker-compose restart         # Neu starten
docker-compose down            # Stoppen
docker-compose up -d --build   # Rebuild und starten
```

### Systemd
```bash
sudo systemctl status stockpredictor       # Status
sudo systemctl restart stockpredictor      # Neu starten
sudo journalctl -u stockpredictor -f       # Logs
sudo systemctl stop stockpredictor         # Stoppen
sudo systemctl start stockpredictor        # Starten
```

### Webhook Receiver
```bash
sudo systemctl status webhook-receiver     # Status
sudo journalctl -u webhook-receiver -f     # Logs
tail -f /var/log/stockpredictor-deploy.log # Deployment-Logs
```

## Troubleshooting

### Port bereits belegt
```bash
# Prozess auf Port 8001 finden und stoppen
sudo lsof -ti:8001 | xargs kill -9
```

### Permission Denied
```bash
sudo chown -R $USER:$USER .
chmod +x deploy.sh setup.sh webhook_receiver.py
```

### Docker Build schlägt fehl
```bash
# Cache löschen und neu bauen
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Service startet nicht
```bash
# Logs überprüfen
sudo journalctl -u stockpredictor --no-pager -n 50
# Config überprüfen
sudo systemctl cat stockpredictor
```

## Nächste Schritte

- 📖 Lesen Sie [README.md](README.md) für detaillierte Funktionsbeschreibung
- 📋 Siehe [INSTALLATION.md](INSTALLATION.md) für erweiterte Konfiguration
- 🔒 Ändern Sie alle Default-Secrets für Produktion!
- 📰 Konfigurieren Sie optional NewsAPI für mehr Nachrichten

## Support

Bei Problemen: https://github.com/NoMadAndy/stockPredictor/issues
