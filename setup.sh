#!/bin/bash

# Stock Predictor Setup Script
# This script helps with initial setup and configuration

set -e

echo "=========================================="
echo "Stock Predictor Setup"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "WARNUNG: Dieses Skript sollte mit sudo ausgeführt werden für vollständige Installation"
    echo ""
fi

# Detect deployment method
echo "Wählen Sie die Deployment-Methode:"
echo "1) Docker (empfohlen)"
echo "2) Systemd Service"
echo "3) Nur Abhängigkeiten prüfen"
read -p "Ihre Wahl [1-3]: " choice

case $choice in
    1)
        echo ""
        echo "=== Docker Deployment ==="
        echo ""
        
        # Check for Docker
        if ! command -v docker &> /dev/null; then
            echo "Docker ist nicht installiert!"
            read -p "Docker jetzt installieren? [y/n]: " install_docker
            if [ "$install_docker" = "y" ]; then
                apt-get update
                apt-get install -y docker.io docker-compose
                systemctl start docker
                systemctl enable docker
                echo "Docker wurde installiert."
            else
                echo "Installation abgebrochen."
                exit 1
            fi
        fi
        
        # Check for docker-compose
        if ! command -v docker-compose &> /dev/null; then
            echo "docker-compose ist nicht installiert!"
            read -p "docker-compose jetzt installieren? [y/n]: " install_compose
            if [ "$install_compose" = "y" ]; then
                apt-get install -y docker-compose
                echo "docker-compose wurde installiert."
            else
                echo "Installation abgebrochen."
                exit 1
            fi
        fi
        
        # Configure secret key
        echo ""
        read -p "Möchten Sie einen SECRET_KEY konfigurieren? [y/n]: " config_secret
        if [ "$config_secret" = "y" ]; then
            read -sp "SECRET_KEY eingeben: " secret_key
            echo ""
            export SECRET_KEY="$secret_key"
            echo "SECRET_KEY wurde gesetzt (nur für diese Session)"
        fi
        
        # Build and start
        echo ""
        echo "Starte Docker Container..."
        docker-compose up -d
        
        echo ""
        echo "✓ Docker Container gestartet!"
        echo "✓ Die Anwendung läuft auf: http://localhost:8001"
        echo ""
        echo "Nützliche Befehle:"
        echo "  - Logs anzeigen: docker-compose logs -f"
        echo "  - Status prüfen: docker-compose ps"
        echo "  - Stoppen: docker-compose down"
        ;;
        
    2)
        echo ""
        echo "=== Systemd Service Deployment ==="
        echo ""
        
        # Check Python
        if ! command -v python3 &> /dev/null; then
            echo "Python 3 ist nicht installiert!"
            exit 1
        fi
        
        # Create virtual environment
        if [ ! -d "venv" ]; then
            echo "Erstelle virtuelle Umgebung..."
            python3 -m venv venv
        fi
        
        # Install dependencies
        echo "Installiere Abhängigkeiten..."
        venv/bin/pip install -r requirements.txt
        
        # Install systemd service
        if [ "$EUID" -eq 0 ]; then
            echo "Installiere systemd Service..."
            cp stockpredictor.service /etc/systemd/system/
            systemctl daemon-reload
            systemctl enable stockpredictor
            
            read -p "Service jetzt starten? [y/n]: " start_service
            if [ "$start_service" = "y" ]; then
                systemctl start stockpredictor
                echo ""
                echo "✓ Service gestartet!"
                echo "✓ Status prüfen mit: systemctl status stockpredictor"
            fi
        else
            echo "HINWEIS: Führen Sie folgende Befehle mit sudo aus:"
            echo "  sudo cp stockpredictor.service /etc/systemd/system/"
            echo "  sudo systemctl daemon-reload"
            echo "  sudo systemctl enable stockpredictor"
            echo "  sudo systemctl start stockpredictor"
        fi
        
        echo ""
        echo "✓ Setup abgeschlossen!"
        echo "✓ Die Anwendung läuft auf: http://localhost:8001"
        ;;
        
    3)
        echo ""
        echo "=== Abhängigkeiten prüfen ==="
        echo ""
        
        # Check Python
        if command -v python3 &> /dev/null; then
            python_version=$(python3 --version)
            echo "✓ Python: $python_version"
        else
            echo "✗ Python 3 nicht gefunden"
        fi
        
        # Check pip
        if command -v pip3 &> /dev/null; then
            pip_version=$(pip3 --version)
            echo "✓ pip: $pip_version"
        else
            echo "✗ pip3 nicht gefunden"
        fi
        
        # Check Docker
        if command -v docker &> /dev/null; then
            docker_version=$(docker --version)
            echo "✓ Docker: $docker_version"
        else
            echo "✗ Docker nicht gefunden"
        fi
        
        # Check docker-compose
        if command -v docker-compose &> /dev/null; then
            compose_version=$(docker-compose --version)
            echo "✓ docker-compose: $compose_version"
        else
            echo "✗ docker-compose nicht gefunden"
        fi
        
        # Check git
        if command -v git &> /dev/null; then
            git_version=$(git --version)
            echo "✓ Git: $git_version"
        else
            echo "✗ Git nicht gefunden"
        fi
        ;;
        
    *)
        echo "Ungültige Auswahl!"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "Setup abgeschlossen!"
echo "=========================================="
echo ""
echo "Weitere Schritte:"
echo "1. Siehe README.md für Nutzungsanleitung"
echo "2. Siehe INSTALLATION.md für Webhook-Setup"
echo "3. Konfigurieren Sie optional NewsAPI in news_api_key.txt"
echo ""
