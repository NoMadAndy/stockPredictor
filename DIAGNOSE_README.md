# yfinance Diagnose-Tool

## Zweck

Das `diagnose_yfinance.py` Skript hilft dabei, Probleme beim Herunterladen von Aktiendaten in der Produktionsumgebung zu identifizieren und einzugrenzen.

## Verwendung

### Grundlegende Verwendung

```bash
python diagnose_yfinance.py [SYMBOL]
```

### Beispiele

```bash
# Test mit AAPL (Standard)
python diagnose_yfinance.py

# Test mit spezifischem Symbol
python diagnose_yfinance.py MSFT

# Test mit deutschem Symbol
python diagnose_yfinance.py DAC
```

## Was wird getestet?

Das Skript führt folgende Tests durch:

### 1. Netzwerk-Konnektivität
- Prüft Verbindung zu Yahoo Finance Servern
- Testet DNS-Auflösung
- Identifiziert Firewall-Probleme

**Mögliche Probleme:**
- Firewall blockiert Port 443
- DNS-Server nicht erreichbar
- Proxy-Server erforderlich

### 2. SSL/TLS-Zertifikate
- Prüft SSL-Verbindung zu Yahoo Finance
- Validiert Zertifikate

**Mögliche Probleme:**
- Veraltete System-Zertifikate
- Corporate Proxy mit SSL-Inspection
- Falsche Systemzeit

### 3. Python-Pakete
- Prüft Installation von yfinance, pandas, requests
- Zeigt Versionen und Pfade an

**Mögliche Probleme:**
- Fehlende oder veraltete Pakete
- Inkompatible Versionen

### 4. Proxy-Einstellungen
- Zeigt konfigurierte Proxy-Umgebungsvariablen

**Mögliche Probleme:**
- Fehlende Proxy-Konfiguration
- Falsche Proxy-Einstellungen

### 5. yfinance Download-Test
- Führt tatsächlichen Download durch
- Zeigt detaillierte Fehlermeldungen

**Mögliche Probleme:**
- Symbol ungültig oder delisted
- API temporär nicht verfügbar
- Rate-Limiting aktiv

### 6. Ticker-Info Test
- Testet Abruf von Ticker-Informationen
- Erkennt JSON-Dekodierungsfehler

**Mögliche Probleme:**
- Ungültiges Symbol
- API-Format geändert

### 7. Test mit Suppression
- Testet Download mit `suppress_yfinance_output()`
- Verifiziert, dass Suppression nicht den Download verhindert

## Ausgabe interpretieren

### ✓ Grün - Test bestanden
Der Test war erfolgreich, kein Problem in diesem Bereich.

### ✗ Rot - Test fehlgeschlagen
In diesem Bereich liegt ein Problem vor. Siehe Empfehlungen.

### ⚠ Gelb - Warnung
Potenzielles Problem oder Test wurde übersprungen.

## Häufige Probleme und Lösungen

### Problem: Keine Netzwerk-Konnektivität

**Symptom:**
```
✗ DNS-Auflösung für query1.finance.yahoo.com fehlgeschlagen
```

**Lösungen:**
1. Prüfen Sie die Firewall-Regeln:
   ```bash
   # Ausgehende HTTPS-Verbindungen (Port 443) müssen erlaubt sein
   sudo iptables -L OUTPUT
   ```

2. Testen Sie DNS-Auflösung:
   ```bash
   nslookup query1.finance.yahoo.com
   dig query1.finance.yahoo.com
   ```

3. Testen Sie direkte Verbindung:
   ```bash
   curl -I https://query1.finance.yahoo.com
   telnet query1.finance.yahoo.com 443
   ```

### Problem: SSL-Fehler

**Symptom:**
```
✗ SSL-Fehler: certificate verify failed
```

**Lösungen:**
1. Aktualisieren Sie CA-Zertifikate:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update && sudo apt-get install ca-certificates
   sudo update-ca-certificates
   
   # RHEL/CentOS
   sudo yum update ca-certificates
   ```

2. Prüfen Sie die Systemzeit:
   ```bash
   date
   # Wenn falsch, synchronisieren:
   sudo ntpdate pool.ntp.org
   ```

3. Bei Corporate Proxy mit SSL-Inspection:
   ```bash
   # Firmen-CA-Zertifikat hinzufügen
   sudo cp corporate-ca.crt /usr/local/share/ca-certificates/
   sudo update-ca-certificates
   ```

### Problem: Proxy erforderlich

**Symptom:**
```
✗ Verbindung zu query1.finance.yahoo.com:443 fehlgeschlagen
```

**Lösungen:**
1. Setzen Sie Proxy-Umgebungsvariablen:
   ```bash
   export HTTP_PROXY="http://proxy.firma.de:8080"
   export HTTPS_PROXY="http://proxy.firma.de:8080"
   export NO_PROXY="localhost,127.0.0.1"
   ```

2. In Python-Code (für requests):
   ```python
   import os
   os.environ['HTTP_PROXY'] = 'http://proxy.firma.de:8080'
   os.environ['HTTPS_PROXY'] = 'http://proxy.firma.de:8080'
   ```

3. Systemweite Konfiguration:
   ```bash
   # /etc/environment
   HTTP_PROXY="http://proxy.firma.de:8080"
   HTTPS_PROXY="http://proxy.firma.de:8080"
   ```

### Problem: Rate-Limiting

**Symptom:**
```
✗ Download fehlgeschlagen: HTTPError: 429 Too Many Requests
```

**Lösungen:**
1. Reduzieren Sie die Anzahl der Anfragen
2. Fügen Sie Verzögerungen zwischen Anfragen ein:
   ```python
   import time
   time.sleep(1)  # 1 Sekunde warten
   ```
3. Verwenden Sie Caching für bereits abgerufene Daten

### Problem: Ungültiges Symbol

**Symptom:**
```
✗ JSON-Dekodierungsfehler
⚠ Dies deutet auf ein ungültiges oder delistetes Symbol hin
```

**Lösungen:**
1. Prüfen Sie das Symbol auf Yahoo Finance Website
2. Testen Sie mit bekannten Symbolen: AAPL, MSFT, GOOGL
3. Verwenden Sie die richtige Börse-Notation (z.B. SAP.DE für deutsche Aktien)

## Automatische Überwachung

Sie können das Skript auch für automatisches Monitoring verwenden:

```bash
#!/bin/bash
# monitoring.sh

# Führe Diagnose aus
python diagnose_yfinance.py AAPL > /var/log/yfinance-check.log 2>&1

# Prüfe Exit-Code
if [ $? -ne 0 ]; then
    echo "yfinance Diagnose fehlgeschlagen!" | mail -s "Alert: yfinance Problem" admin@firma.de
fi
```

Als Cronjob:
```cron
# Täglich um 6:00 Uhr prüfen
0 6 * * * /opt/stockpredictor/monitoring.sh
```

## Integration in Produktionscode

Sie können die Tests auch programmatisch verwenden:

```python
import subprocess
import sys

def check_yfinance_health():
    """Prüft ob yfinance funktionsfähig ist"""
    result = subprocess.run(
        [sys.executable, 'diagnose_yfinance.py', 'AAPL'],
        capture_output=True,
        timeout=30
    )
    return result.returncode == 0

# Vor wichtigen Downloads prüfen
if check_yfinance_health():
    # Download durchführen
    pass
else:
    # Fallback oder Warnung
    logging.warning("yfinance nicht verfügbar")
```

## Fehlerberichterstattung

Wenn Sie einen Bug melden möchten, führen Sie bitte aus:

```bash
python diagnose_yfinance.py YOUR_SYMBOL > diagnose-output.txt 2>&1
```

Und fügen Sie die `diagnose-output.txt` dem Bug-Report bei.

## Weitere Debugging-Tipps

### Verbose Logging für yfinance aktivieren

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Network Traffic analysieren

```bash
# tcpdump verwenden
sudo tcpdump -i any -w yfinance-traffic.pcap host query1.finance.yahoo.com

# Wireshark für Analyse
wireshark yfinance-traffic.pcap
```

### Python Requests debugging

```python
import requests
import logging

# Enable HTTP request logging
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
```

## Support

Bei weiteren Fragen oder Problemen:
1. Konsultieren Sie die yfinance Dokumentation: https://pypi.org/project/yfinance/
2. Prüfen Sie bekannte Issues: https://github.com/ranaroussi/yfinance/issues
3. Erstellen Sie ein Issue in diesem Repository mit der Diagnose-Ausgabe
