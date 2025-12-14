# Installation & Deployment Guide

Diese Anleitung beschreibt die Installation und Einrichtung des Stock Predictor mit automatischem Deployment.

## Voraussetzungen

- Linux Server (Ubuntu/Debian empfohlen)
- Python 3.8+
- Git
- Optional: Docker & Docker Compose
- Sudo/Root-Zugriff für Systemd-Services

## Option 1: Docker Deployment (Empfohlen)

### Installation

```bash
# Docker und Docker Compose installieren (falls nicht vorhanden)
sudo apt-get update
sudo apt-get install -y docker.io docker-compose

# Repository klonen
sudo git clone https://github.com/NoMadAndy/stockPredictor.git /opt/stockpredictor
cd /opt/stockpredictor

# Optional: NewsAPI Key konfigurieren
echo "YOUR_NEWS_API_KEY" > news_api_key.txt

# Secret Key setzen
export SECRET_KEY="your-secure-random-key"

# Container starten
sudo docker-compose up -d
```

### Überprüfung

```bash
# Container-Status prüfen
sudo docker-compose ps

# Logs anzeigen
sudo docker-compose logs -f

# Anwendung testen
curl http://localhost:8001
```

## Option 2: Systemd Service Deployment

### Installation

```bash
# System aktualisieren
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git

# Repository klonen
sudo git clone https://github.com/NoMadAndy/stockPredictor.git /opt/stockpredictor
cd /opt/stockpredictor

# Virtuelle Umgebung erstellen
sudo python3 -m venv venv
sudo venv/bin/pip install -r requirements.txt

# Berechtigungen setzen
sudo chown -R www-data:www-data /opt/stockpredictor
sudo chmod +x deploy.sh

# Systemd Service installieren
sudo cp stockpredictor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable stockpredictor
sudo systemctl start stockpredictor
```

### Überprüfung

```bash
# Service-Status prüfen
sudo systemctl status stockpredictor

# Logs anzeigen
sudo journalctl -u stockpredictor -f

# Anwendung testen
curl http://localhost:8001
```

## Auto-Deployment mit GitHub Webhooks

### 1. Webhook Receiver installieren

```bash
# Systemd Service für Webhook Receiver installieren
sudo cp webhook-receiver.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable webhook-receiver
sudo systemctl start webhook-receiver
```

### 2. Webhook Secret generieren

```bash
# Zufälliges Secret generieren
WEBHOOK_SECRET=$(openssl rand -hex 32)
echo $WEBHOOK_SECRET

# Secret in Service-Datei eintragen
sudo nano /etc/systemd/system/webhook-receiver.service
# Ersetzen Sie "change_this_in_production" mit dem generierten Secret

# Service neu starten
sudo systemctl restart webhook-receiver
```

### 3. GitHub Webhook konfigurieren

1. Gehen Sie zu Ihrem Repository auf GitHub
2. Klicken Sie auf "Settings" → "Webhooks" → "Add webhook"
3. Konfigurieren Sie:
   - **Payload URL**: `http://ihr-server:9001/webhook`
   - **Content type**: `application/json`
   - **Secret**: Das generierte WEBHOOK_SECRET
   - **Events**: Wählen Sie "Just the push event"
4. Klicken Sie auf "Add webhook"

### 4. Firewall konfigurieren (falls aktiviert)

```bash
# Port 8001 für die Anwendung öffnen
sudo ufw allow 8001/tcp

# Port 9001 für den Webhook Receiver öffnen
sudo ufw allow 9001/tcp
```

### 5. Testen

```bash
# Webhook Receiver Logs überprüfen
sudo journalctl -u webhook-receiver -f

# Einen Test-Commit pushen
git commit --allow-empty -m "Test deployment"
git push

# Deployment-Logs überprüfen
tail -f /var/log/stockpredictor-deploy.log
```

## Reverse Proxy mit Nginx (Optional)

Falls Sie die Anwendung hinter einem Nginx Reverse Proxy betreiben möchten:

```bash
# Nginx installieren
sudo apt-get install -y nginx

# Nginx-Konfiguration erstellen
sudo nano /etc/nginx/sites-available/stockpredictor
```

Inhalt der Konfiguration:

```nginx
server {
    listen 80;
    server_name ihr-domain.de;

    location / {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket Support für Socket.IO
    location /socket.io/ {
        proxy_pass http://localhost:8001/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Webhook Receiver
server {
    listen 80;
    server_name webhook.ihr-domain.de;

    location /webhook {
        proxy_pass http://localhost:9001/webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Aktivieren und starten:

```bash
# Konfiguration aktivieren
sudo ln -s /etc/nginx/sites-available/stockpredictor /etc/nginx/sites-enabled/

# Nginx testen und neu laden
sudo nginx -t
sudo systemctl reload nginx
```

## SSL/TLS mit Let's Encrypt (Empfohlen für Produktion)

```bash
# Certbot installieren
sudo apt-get install -y certbot python3-certbot-nginx

# SSL-Zertifikat erhalten und automatisch konfigurieren
sudo certbot --nginx -d ihr-domain.de -d webhook.ihr-domain.de

# Automatische Erneuerung testen
sudo certbot renew --dry-run
```

## Wartung

### Logs überprüfen

```bash
# Anwendungs-Logs
sudo journalctl -u stockpredictor -n 100

# Webhook Receiver Logs
sudo journalctl -u webhook-receiver -n 100

# Deployment-Logs
sudo tail -f /var/log/stockpredictor-deploy.log
```

### Manuelles Update

```bash
cd /opt/stockpredictor
sudo git pull
sudo systemctl restart stockpredictor
```

### Service neu starten

```bash
# Anwendung neu starten
sudo systemctl restart stockpredictor

# Webhook Receiver neu starten
sudo systemctl restart webhook-receiver
```

## Troubleshooting

### Port bereits in Verwendung

```bash
# Prüfen, welcher Prozess Port 8001 verwendet
sudo lsof -i :8001
sudo netstat -tulpn | grep 8001
```

### Permission Denied Fehler

```bash
# Berechtigungen korrigieren
sudo chown -R www-data:www-data /opt/stockpredictor
sudo chmod +x /opt/stockpredictor/deploy.sh
```

### Deployment schlägt fehl

```bash
# Deployment-Log überprüfen
sudo tail -f /var/log/stockpredictor-deploy.log

# Manuell ausführen zum Debuggen
sudo bash -x /opt/stockpredictor/deploy.sh
```

## Support

Bei Problemen erstellen Sie bitte ein Issue im GitHub Repository:
https://github.com/NoMadAndy/stockPredictor/issues
