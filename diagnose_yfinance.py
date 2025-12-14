#!/usr/bin/env python3
"""
Diagnose-Tool für yfinance Download-Probleme
==============================================

Dieses Skript hilft dabei, Probleme beim Herunterladen von Aktiendaten zu identifizieren.
Es testet verschiedene potenzielle Fehlerquellen und gibt detaillierte Diagnoseinformationen aus.

Verwendung:
    python diagnose_yfinance.py [SYMBOL]
    
Beispiel:
    python diagnose_yfinance.py AAPL
"""

import sys
import os
from datetime import datetime, timedelta
import socket
import ssl

# Farben für Terminal-Ausgabe
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(text):
    print(f"  {text}")


def check_network_connectivity():
    """Prüft die grundlegende Netzwerkkonnektivität"""
    print_header("1. NETZWERK-KONNEKTIVITÄT")
    
    hosts_to_check = [
        ("query1.finance.yahoo.com", 443),
        ("query2.finance.yahoo.com", 443),
        ("fc.yahoo.com", 443),
        ("finance.yahoo.com", 443),
    ]
    
    success_count = 0
    for host, port in hosts_to_check:
        try:
            socket.setdefaulttimeout(5)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print_success(f"Verbindung zu {host}:{port} erfolgreich")
                success_count += 1
            else:
                print_error(f"Verbindung zu {host}:{port} fehlgeschlagen (Code: {result})")
        except socket.gaierror:
            print_error(f"DNS-Auflösung für {host} fehlgeschlagen")
        except Exception as e:
            print_error(f"Fehler bei {host}:{port} - {type(e).__name__}: {e}")
    
    if success_count == 0:
        print_warning("Keine Verbindung zu Yahoo Finance Servern möglich!")
        print_info("Mögliche Ursachen:")
        print_info("  - Firewall blockiert ausgehende Verbindungen")
        print_info("  - Proxy-Server erforderlich (aber nicht konfiguriert)")
        print_info("  - DNS-Server nicht erreichbar")
        print_info("  - Keine Internet-Verbindung")
    
    return success_count > 0


def check_ssl_certificates():
    """Prüft SSL/TLS-Zertifikate"""
    print_header("2. SSL/TLS-ZERTIFIKATE")
    
    try:
        context = ssl.create_default_context()
        with socket.create_connection(("query1.finance.yahoo.com", 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname="query1.finance.yahoo.com") as ssock:
                cert = ssock.getpeercert()
                print_success("SSL-Verbindung zu Yahoo Finance erfolgreich")
                print_info(f"Zertifikat: {cert.get('subject', 'N/A')}")
                print_info(f"Ausgestellt von: {cert.get('issuer', 'N/A')}")
                return True
    except ssl.SSLError as e:
        print_error(f"SSL-Fehler: {e}")
        print_warning("Mögliche Ursachen:")
        print_info("  - Veraltete SSL-Zertifikate im System")
        print_info("  - Corporate Proxy mit SSL-Inspection")
        print_info("  - Systemzeit ist falsch eingestellt")
        return False
    except Exception as e:
        print_error(f"Verbindungsfehler: {type(e).__name__}: {e}")
        return False


def check_python_packages():
    """Prüft installierte Python-Pakete"""
    print_header("3. PYTHON-PAKETE")
    
    required_packages = {
        'yfinance': '0.2.0',
        'pandas': '1.0.0',
        'requests': '2.20.0',
    }
    
    all_ok = True
    for package, min_version in required_packages.items():
        try:
            module = __import__(package)
            version = getattr(module, '__version__', 'unbekannt')
            print_success(f"{package}: {version}")
            print_info(f"  Installationspfad: {module.__file__}")
        except ImportError:
            print_error(f"{package} ist nicht installiert!")
            print_info(f"  Installation: pip install {package}>={min_version}")
            all_ok = False
    
    return all_ok


def check_proxy_settings():
    """Prüft Proxy-Einstellungen"""
    print_header("4. PROXY-EINSTELLUNGEN")
    
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'NO_PROXY', 'no_proxy']
    found_proxy = False
    
    for var in proxy_vars:
        value = os.environ.get(var)
        if value:
            print_info(f"{var} = {value}")
            found_proxy = True
    
    if not found_proxy:
        print_info("Keine Proxy-Umgebungsvariablen gesetzt")
    
    return True


def test_yfinance_download(symbol="AAPL"):
    """Testet den tatsächlichen Download mit yfinance"""
    print_header(f"5. YFINANCE DOWNLOAD-TEST ({symbol})")
    
    try:
        import yfinance as yf
        import pandas as pd
        
        print_info("Versuche Daten herunterzuladen...")
        
        # Test 1: Kurzer Zeitraum
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print_info(f"Zeitraum: {start_date.date()} bis {end_date.date()}")
        
        # Download mit sichtbaren Fehlermeldungen
        df = yf.download(symbol, start=start_date, end=end_date, progress=False)
        
        if df is not None and not df.empty:
            print_success(f"Download erfolgreich: {len(df)} Zeilen")
            print_info(f"Spalten: {list(df.columns)}")
            print_info(f"Erste Zeile: {df.iloc[0].to_dict()}")
            return True
        else:
            print_error("Download lieferte leeres DataFrame")
            return False
            
    except ImportError as e:
        print_error(f"Import-Fehler: {e}")
        return False
    except Exception as e:
        print_error(f"Download fehlgeschlagen: {type(e).__name__}: {e}")
        print_info(f"Vollständiger Fehler: {str(e)}")
        return False


def test_ticker_info(symbol="AAPL"):
    """Testet den Zugriff auf Ticker-Informationen"""
    print_header(f"6. TICKER-INFO TEST ({symbol})")
    
    try:
        import yfinance as yf
        import json
        
        print_info("Versuche Ticker-Informationen abzurufen...")
        ticker = yf.Ticker(symbol)
        
        try:
            info = ticker.info
            if info:
                print_success("Ticker-Info erfolgreich abgerufen")
                print_info(f"Name: {info.get('shortName', 'N/A')}")
                print_info(f"Währung: {info.get('currency', 'N/A')}")
                print_info(f"Market Cap: {info.get('marketCap', 'N/A')}")
                return True
            else:
                print_warning("Ticker-Info ist leer")
                return False
        except json.JSONDecodeError as e:
            print_error(f"JSON-Dekodierungsfehler: {e}")
            print_warning("Dies deutet auf ein ungültiges oder delistetes Symbol hin")
            return False
        except Exception as e:
            print_error(f"Fehler beim Abrufen der Ticker-Info: {type(e).__name__}: {e}")
            return False
            
    except Exception as e:
        print_error(f"Ticker-Test fehlgeschlagen: {type(e).__name__}: {e}")
        return False


def test_with_suppression(symbol="AAPL"):
    """Testet Download mit unserer Suppression"""
    print_header(f"7. TEST MIT SUPPRESSION ({symbol})")
    
    try:
        # Versuche utils.py zu importieren
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from utils import suppress_yfinance_output
        import yfinance as yf
        from datetime import datetime, timedelta
        
        print_info("Teste Download mit suppress_yfinance_output()...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        with suppress_yfinance_output():
            df = yf.download(symbol, start=start_date, end=end_date, progress=False)
        
        if df is not None and not df.empty:
            print_success(f"Download mit Suppression erfolgreich: {len(df)} Zeilen")
            return True
        else:
            print_error("Download mit Suppression lieferte leeres DataFrame")
            return False
            
    except ImportError:
        print_warning("utils.py nicht gefunden (nur relevant wenn im Projekt-Verzeichnis)")
        return None
    except Exception as e:
        print_error(f"Fehler: {type(e).__name__}: {e}")
        return False


def print_recommendations(results):
    """Gibt Empfehlungen basierend auf den Test-Ergebnissen"""
    print_header("EMPFEHLUNGEN")
    
    if not results.get('network'):
        print("🔧 NETZWERK-PROBLEM:")
        print_info("  1. Prüfen Sie die Firewall-Einstellungen")
        print_info("  2. Testen Sie: curl -I https://query1.finance.yahoo.com")
        print_info("  3. Prüfen Sie, ob ein Proxy erforderlich ist")
        print_info("  4. Überprüfen Sie DNS-Einstellungen: nslookup query1.finance.yahoo.com")
        print()
    
    if not results.get('ssl'):
        print("🔧 SSL/TLS-PROBLEM:")
        print_info("  1. Aktualisieren Sie SSL-Zertifikate: sudo update-ca-certificates")
        print_info("  2. Prüfen Sie die Systemzeit: date")
        print_info("  3. Bei Corporate Proxy: CA-Zertifikat installieren")
        print()
    
    if not results.get('packages'):
        print("🔧 PAKET-PROBLEM:")
        print_info("  1. Installieren Sie fehlende Pakete: pip install -r requirements.txt")
        print_info("  2. Aktualisieren Sie yfinance: pip install --upgrade yfinance")
        print()
    
    if results.get('network') and results.get('ssl') and results.get('packages'):
        if not results.get('download'):
            print("🔧 YFINANCE-SPEZIFISCHES PROBLEM:")
            print_info("  1. Das Symbol könnte ungültig oder delisted sein")
            print_info("  2. Testen Sie mit einem anderen Symbol: AAPL, MSFT, GOOGL")
            print_info("  3. Yahoo Finance API könnte temporär nicht verfügbar sein")
            print_info("  4. Rate-Limiting könnte aktiv sein (zu viele Anfragen)")
            print()
        else:
            print_success("Alle Tests bestanden! yfinance funktioniert korrekt.")
            print_info("Falls Probleme auftreten:")
            print_info("  - Prüfen Sie die Logs auf spezifische Fehlermeldungen")
            print_info("  - Testen Sie mit verschiedenen Symbolen")
            print_info("  - Prüfen Sie auf Rate-Limiting bei vielen Anfragen")


def main():
    """Hauptfunktion"""
    print(f"\n{Colors.BOLD}Diagnose-Tool für yfinance Download-Probleme{Colors.RESET}")
    print(f"Zeitpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Symbol aus Kommandozeile oder Standard
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    
    # Führe alle Tests durch
    results = {}
    results['network'] = check_network_connectivity()
    results['ssl'] = check_ssl_certificates()
    results['packages'] = check_python_packages()
    results['proxy'] = check_proxy_settings()
    results['download'] = test_yfinance_download(symbol)
    results['ticker'] = test_ticker_info(symbol)
    results['suppression'] = test_with_suppression(symbol)
    
    # Zusammenfassung
    print_header("ZUSAMMENFASSUNG")
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    print(f"Tests bestanden: {Colors.GREEN}{passed}{Colors.RESET}")
    print(f"Tests fehlgeschlagen: {Colors.RED}{failed}{Colors.RESET}")
    print(f"Tests übersprungen: {Colors.YELLOW}{skipped}{Colors.RESET}")
    
    # Empfehlungen
    print_recommendations(results)
    
    # Exit code
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
