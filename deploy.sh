#!/bin/bash

# Stock Predictor Auto-Deployment Script
# This script pulls the latest changes from GitHub and restarts the application

set -e

APP_DIR="/opt/stockpredictor"
LOG_FILE="/var/log/stockpredictor-deploy.log"
BRANCH="main"

echo "$(date): Starting deployment..." | tee -a "$LOG_FILE"

# Navigate to app directory
cd "$APP_DIR" || exit 1

# Stash any local changes
git stash

# Pull latest changes
echo "$(date): Pulling latest changes from GitHub..." | tee -a "$LOG_FILE"
git pull origin "$BRANCH" 2>&1 | tee -a "$LOG_FILE"

# Check if docker-compose is available
if command -v docker-compose &> /dev/null; then
    echo "$(date): Rebuilding and restarting Docker containers..." | tee -a "$LOG_FILE"
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    echo "$(date): Docker deployment completed successfully!" | tee -a "$LOG_FILE"
elif systemctl is-active --quiet stockpredictor; then
    echo "$(date): Installing/updating dependencies..." | tee -a "$LOG_FILE"
    # Activate virtual environment if it exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    pip install -r requirements.txt 2>&1 | tee -a "$LOG_FILE"
    
    echo "$(date): Restarting systemd service..." | tee -a "$LOG_FILE"
    systemctl restart stockpredictor
    echo "$(date): Systemd deployment completed successfully!" | tee -a "$LOG_FILE"
else
    echo "$(date): ERROR - No deployment method available (Docker or systemd)" | tee -a "$LOG_FILE"
    exit 1
fi

echo "$(date): Deployment completed!" | tee -a "$LOG_FILE"
