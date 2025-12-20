# CI/CD und Automatisches Deployment Guide

Dieses Dokument beschreibt die vollständige CI/CD-Pipeline und automatische Deployment-Lösung für Stock Predictor.

## Übersicht

Die Lösung besteht aus mehreren Komponenten:

1. **GitHub Actions Workflows** - Automatische Tests und Deployments
2. **Webhook Receiver** - Empfängt GitHub-Events und löst Deployments aus
3. **Deployment Script** - Führt das eigentliche Deployment durch
4. **Health Checks** - Verifiziert erfolgreiche Deployments

## Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                         GitHub Repository                        │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ├──► Push to main → GitHub Actions → Preprod Server
                               │
                               └──► Release → GitHub Actions → Production Server
                                          │
                                          └──► Webhook → Production Server
```

## Umgebungen

### Preprod (Preproduction)
- **Trigger**: Push zu `main` Branch
- **Deployment**: Automatisch
- **Server**: Ubuntu VM unter `/opt/stockpredictor`
- **Verwendung**: Testing und Validierung vor Production

### Production
- **Trigger**: GitHub Release (Tag)
- **Deployment**: Mit manuellem Approval Gate
- **Server**: Ubuntu VM unter `/opt/stockpredictor`
- **Verwendung**: Live-Umgebung für Endbenutzer

## Installation

### 1. Server-Setup für Preprod

```bash
# Als root oder mit sudo auf dem Preprod-Server
sudo wget https://raw.githubusercontent.com/NoMadAndy/stockPredictor/main/install-server.sh
sudo chmod +x install-server.sh
sudo ./install-server.sh preprod
```

Das Skript wird:
- System-Packages installieren
- Repository nach `/opt/stockpredictor` klonen
- Python Virtual Environment erstellen
- Dependencies installieren
- Sichere Secrets generieren
- Systemd Services konfigurieren
- Firewall einrichten
- Nginx Reverse Proxy konfigurieren
- Services starten

**Wichtig**: Notieren Sie die generierten Secrets (SECRET_KEY, WEBHOOK_SECRET, API_KEY_ENCRYPTION_SECRET)!

### 2. Server-Setup für Production

```bash
# Als root oder mit sudo auf dem Production-Server
sudo wget https://raw.githubusercontent.com/NoMadAndy/stockPredictor/main/install-server.sh
sudo chmod +x install-server.sh
sudo ./install-server.sh production
```

### 3. GitHub Secrets konfigurieren

Fügen Sie folgende Secrets in Ihrem GitHub Repository hinzu:
(Settings → Secrets and variables → Actions → New repository secret)

#### Für Preprod:
- `PREPROD_SERVER`: IP-Adresse oder Hostname des Preprod-Servers
- `PREPROD_SSH_USER`: SSH-Benutzername (z.B. `root` oder `ubuntu`)
- `PREPROD_SSH_KEY`: Private SSH-Key für Zugriff auf Preprod-Server
- `PREPROD_SSH_PORT`: SSH-Port (optional, Standard: 22)

#### Für Production:
- `PROD_SERVER`: IP-Adresse oder Hostname des Production-Servers
- `PROD_SSH_USER`: SSH-Benutzername
- `PROD_SSH_KEY`: Private SSH-Key für Zugriff auf Production-Server
- `PROD_SSH_PORT`: SSH-Port (optional, Standard: 22)

#### SSH-Key generieren (falls noch nicht vorhanden):

```bash
# Auf Ihrem lokalen Rechner
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy_key

# Public Key auf Server kopieren
ssh-copy-id -i ~/.ssh/github_deploy_key.pub user@preprod-server
ssh-copy-id -i ~/.ssh/github_deploy_key.pub user@prod-server

# Private Key als GitHub Secret hinzufügen
cat ~/.ssh/github_deploy_key  # Kopieren und als Secret einfügen
```

### 4. GitHub Webhook konfigurieren (Optional - zusätzlich zu Actions)

Gehen Sie zu: Repository → Settings → Webhooks → Add webhook

#### Preprod Webhook:
- **Payload URL**: `http://PREPROD_SERVER:9001/webhook`
- **Content type**: `application/json`
- **Secret**: Der `WEBHOOK_SECRET` vom Preprod-Server
- **Events**: Just the push event
- **Active**: ✓

#### Production Webhook:
- **Payload URL**: `http://PROD_SERVER:9001/webhook`
- **Content type**: `application/json`
- **Secret**: Der `WEBHOOK_SECRET` vom Production-Server
- **Events**: Let me select individual events → Releases
- **Active**: ✓

**Hinweis**: Der Webhook ist optional, da GitHub Actions bereits Deployments durchführt. Der Webhook bietet eine zusätzliche direkte Deployment-Methode.

## GitHub Actions Workflows

### CI Workflow (`.github/workflows/ci.yml`)

Läuft bei jedem Push und Pull Request:
- Installiert Dependencies
- Verifiziert Imports
- Testet Anwendungsstart
- Baut Docker Image
- Testet Docker Container

### Preprod Deployment (`.github/workflows/deploy-preprod.yml`)

Läuft automatisch bei Push zu `main`:
1. Verbindet via SSH zum Preprod-Server
2. Pulled neueste Änderungen
3. Führt Deployment-Script aus
4. Führt Health Check durch
5. Benachrichtigt über Erfolg/Fehler

Manueller Trigger:
```bash
# Über GitHub UI: Actions → Deploy to Preprod → Run workflow
```

### Production Deployment (`.github/workflows/deploy-prod.yml`)

Läuft bei GitHub Release:
1. Wartet auf manuelle Approval (falls Environment Protection konfiguriert)
2. Erstellt Backup der aktuellen Version
3. Checkt spezifische Version aus (Tag)
4. Führt Deployment-Script aus
5. Führt erweiterte Health Checks durch
6. Rollt bei Fehler automatisch zurück

Manueller Trigger:
```bash
# Über GitHub UI: Actions → Deploy to Production → Run workflow
# Version/Tag eingeben (z.B., v1.0.0 oder main)
```

## Deployment-Prozess

### Automatischer Deployment-Ablauf:

```
1. Code-Änderung gepusht
   │
   ├─► CI Tests laufen
   │   ├─► Python Tests
   │   └─► Docker Build
   │
2. Push zu main Branch
   │
   ├─► GitHub Actions Preprod Deployment
   │   ├─► SSH zu Preprod-Server
   │   ├─► Git Pull
   │   ├─► Deployment Script
   │   │   ├─► Dependencies Update
   │   │   ├─► Service Restart
   │   │   └─► Health Check
   │   └─► Notification
   │
3. Release erstellen
   │
   └─► GitHub Actions Production Deployment
       ├─► Manual Approval (optional)
       ├─► SSH zu Production-Server
       ├─► Backup erstellen
       ├─► Git Checkout Tag
       ├─► Deployment Script
       │   ├─► Dependencies Update
       │   ├─► Service Restart
       │   └─► Health Checks
       └─► Rollback bei Fehler
```

### Deployment Script Details (`deploy.sh`)

Das Deployment-Script:
- Unterstützt verschiedene Umgebungen (DEPLOYMENT_ENV)
- Pulled/checkt spezifische Git-Refs aus
- Unterstützt Docker und Systemd Deployments
- Führt automatische Health Checks durch
- Rollt bei Fehlern zurück
- Logged alle Aktionen nach `/var/log/stockpredictor-deploy.log`

### Webhook Receiver Details (`webhook_receiver.py`)

Der Webhook Receiver:
- Läuft als Systemd Service auf Port 9001
- Verifiziert GitHub Webhook Signaturen
- Unterscheidet zwischen Umgebungen:
  - **Preprod**: Reagiert auf Push zu main
  - **Production**: Reagiert auf Release Events
- Triggert Deployment-Script mit Kontext
- Logged alle Events nach `/var/log/webhook-receiver.log`

## Deployment durchführen

### Preprod Deployment:

**Automatisch:**
```bash
# Einfach Code zu main pushen
git push origin main
```

**Manuell:**
```bash
# Über GitHub Actions
# 1. Gehe zu: Actions → Deploy to Preprod → Run workflow
# 2. Klicke "Run workflow"

# Oder direkt auf dem Server
ssh user@preprod-server
sudo /opt/stockpredictor/deploy.sh
```

### Production Deployment:

**Release erstellen:**
```bash
# 1. Tag erstellen und pushen
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# 2. Auf GitHub: Releases → Draft a new release
#    - Tag: v1.0.0
#    - Title: Version 1.0.0
#    - Description: Release notes
#    - Publish release

# 3. GitHub Actions startet automatisch Production Deployment
```

**Manuell via Actions:**
```bash
# 1. Gehe zu: Actions → Deploy to Production → Run workflow
# 2. Gebe Version/Tag ein (z.B., v1.0.0)
# 3. Klicke "Run workflow"
# 4. Approve Deployment (falls Environment Protection aktiv)
```

## Monitoring und Troubleshooting

### Logs überprüfen

#### Application Logs:
```bash
# Systemd Logs
journalctl -u stockpredictor -f

# Oder direkte Log-Dateien
tail -f /var/log/stockpredictor.log
tail -f /var/log/stockpredictor-error.log
```

#### Webhook Receiver Logs:
```bash
journalctl -u webhook-receiver -f

# Oder
tail -f /var/log/webhook-receiver.log
```

#### Deployment Logs:
```bash
tail -f /var/log/stockpredictor-deploy.log
```

#### GitHub Actions Logs:
```bash
# Auf GitHub: Actions → Wähle Workflow Run → Siehe Logs
```

### Service Status überprüfen

```bash
# Application Status
systemctl status stockpredictor

# Webhook Receiver Status
systemctl status webhook-receiver

# Nginx Status
systemctl status nginx
```

### Health Checks

```bash
# Application Health
curl http://localhost:8001/health

# Webhook Receiver Health
curl http://localhost:9001/health

# Via öffentlicher IP
curl http://YOUR_SERVER:8001/health
```

### Häufige Probleme

#### Deployment schlägt fehl

```bash
# Deployment-Logs prüfen
tail -100 /var/log/stockpredictor-deploy.log

# Service manuell neu starten
systemctl restart stockpredictor

# Manuell deployen zum Debuggen
sudo bash -x /opt/stockpredictor/deploy.sh
```

#### Health Check schlägt fehl

```bash
# Application-Logs prüfen
journalctl -u stockpredictor -n 100

# Prüfen ob Service läuft
systemctl status stockpredictor

# Port-Bindung prüfen
netstat -tulpn | grep 8001
```

#### Webhook wird nicht empfangen

```bash
# Webhook Receiver Logs prüfen
journalctl -u webhook-receiver -n 100

# Prüfen ob Service läuft
systemctl status webhook-receiver

# Firewall-Regel prüfen
ufw status | grep 9001

# Von extern testen
curl http://YOUR_SERVER:9001/health
```

#### SSH-Verbindung in GitHub Actions schlägt fehl

```bash
# SSH-Key auf Server verifizieren
cat ~/.ssh/authorized_keys

# SSH manuell testen
ssh -i /path/to/key user@server

# Permissions prüfen
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

### Rollback durchführen

#### Automatischer Rollback:
Bei fehlgeschlagenem Health Check rollt das Deployment-Script automatisch zurück.

#### Manueller Rollback auf vorherige Version:

```bash
# Auf dem Server
cd /opt/stockpredictor

# Liste verfügbarer Versionen
git tag -l

# Checkout vorherige Version
sudo git checkout v1.0.0  # oder anderen Tag/Branch

# Deployment durchführen
sudo /opt/stockpredictor/deploy.sh

# Service neu starten
sudo systemctl restart stockpredictor
```

#### Rollback via GitHub Actions:
```bash
# 1. Gehe zu: Actions → Deploy to Production → Run workflow
# 2. Gebe vorherige Version ein (z.B., v0.9.0)
# 3. Klicke "Run workflow"
```

## Sicherheit

### Best Practices

1. **Secrets Management**
   - Verwenden Sie starke, zufällige Secrets
   - Speichern Sie Secrets sicher (nicht in Git)
   - Rotieren Sie Secrets regelmäßig

2. **SSH-Keys**
   - Verwenden Sie separate Keys für Deployment
   - Beschränken Sie Key-Berechtigungen auf spezifische Server
   - Verwenden Sie Ed25519 Keys (stärker und schneller)

3. **Firewall**
   - Erlauben Sie nur benötigte Ports
   - Beschränken Sie SSH-Zugriff auf bekannte IPs
   - Verwenden Sie fail2ban für SSH-Schutz

4. **HTTPS**
   - Verwenden Sie SSL/TLS in Production
   - Installieren Sie Let's Encrypt Zertifikate
   - Erzwingen Sie HTTPS-Redirect

5. **Webhook-Signaturen**
   - Aktivieren Sie immer Webhook-Secrets
   - Verifizieren Sie Signaturen im Receiver
   - Lehnen Sie nicht-signierte Requests ab

### SSL/TLS mit Let's Encrypt einrichten

```bash
# Certbot installieren
sudo apt-get install -y certbot python3-certbot-nginx

# Zertifikat erhalten
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Automatische Erneuerung testen
sudo certbot renew --dry-run

# Nginx-Konfiguration wird automatisch aktualisiert
```

## Wartung

### Regelmäßige Aufgaben

#### Wöchentlich:
- Logs überprüfen auf Fehler
- Deployment-History auf GitHub Actions prüfen
- Health Checks manuell durchführen

#### Monatlich:
- System-Updates durchführen
- Logs archivieren/rotieren
- Backup-Strategie verifizieren
- Secrets rotieren

### System-Updates

```bash
# Sicherheits-Updates installieren
sudo apt-get update
sudo apt-get upgrade -y

# Services neu starten falls nötig
sudo systemctl restart stockpredictor
sudo systemctl restart webhook-receiver
sudo systemctl restart nginx
```

### Logs rotieren

```bash
# Logrotate-Konfiguration erstellen
sudo nano /etc/logrotate.d/stockpredictor
```

Inhalt:
```
/var/log/stockpredictor*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload stockpredictor > /dev/null 2>&1 || true
    endscript
}

/var/log/webhook-receiver*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        systemctl reload webhook-receiver > /dev/null 2>&1 || true
    endscript
}
```

## Erweiterte Konfiguration

### Environment Protection (GitHub)

Für zusätzliche Sicherheit in Production:

1. Gehe zu: Repository → Settings → Environments
2. Klicke auf "production" Environment
3. Aktiviere "Required reviewers"
4. Füge Reviewer hinzu
5. Optional: Aktiviere "Wait timer" für verzögertes Deployment

### Blue-Green Deployment (Optional)

Für zero-downtime Deployments:

1. Zweite Instanz auf anderem Port starten
2. Health Check durchführen
3. Nginx auf neue Instanz umschalten
4. Alte Instanz stoppen

### Monitoring mit Prometheus/Grafana (Optional)

Für erweitertes Monitoring:

1. Prometheus Server installieren
2. Node Exporter auf Servern installieren
3. Grafana Dashboard erstellen
4. Alerts konfigurieren

## Support

Bei Fragen oder Problemen:

1. Prüfen Sie die Logs
2. Suchen Sie in GitHub Issues
3. Erstellen Sie ein neues Issue mit:
   - Umgebung (preprod/production)
   - Fehlerlog
   - Schritte zur Reproduktion
   - Erwartetes vs. tatsächliches Verhalten

## Zusammenfassung

Die CI/CD-Pipeline bietet:

✅ Automatische Tests bei jedem Push
✅ Automatisches Deployment zu Preprod bei Push zu main
✅ Kontrolliertes Deployment zu Production via Releases
✅ Health Checks und automatisches Rollback
✅ Umfassendes Logging und Monitoring
✅ Webhook-basierte alternative Deployment-Methode
✅ Sicherheit durch Secrets und Signaturen
✅ Einfache Installation mit `install-server.sh`

Die Lösung ermöglicht schnelle Iteration in Preprod und sichere, kontrollierte Deployments in Production.
