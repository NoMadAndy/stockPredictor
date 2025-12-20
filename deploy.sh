#!/bin/bash

# Stock Predictor Auto-Deployment Script
# This script pulls the latest changes from GitHub and restarts the application

set -e

APP_DIR="/opt/stockpredictor"
LOG_FILE="/var/log/stockpredictor-deploy.log"
BRANCH="${GIT_REF:-main}"  # Use GIT_REF from webhook or default to main
DEPLOYMENT_ENV="${DEPLOYMENT_ENV:-preprod}"  # Default to preprod

echo "$(date): ============================================" | tee -a "$LOG_FILE"
echo "$(date): Starting deployment to ${DEPLOYMENT_ENV}..." | tee -a "$LOG_FILE"
echo "$(date): ============================================" | tee -a "$LOG_FILE"

# Navigate to app directory
cd "$APP_DIR" || exit 1

# Parse branch/tag from GIT_REF if it's a full ref
if [[ "$BRANCH" == refs/heads/* ]]; then
    BRANCH="${BRANCH#refs/heads/}"
elif [[ "$BRANCH" == refs/tags/* ]]; then
    BRANCH="${BRANCH#refs/tags/}"
fi

echo "$(date): Target ref: $BRANCH" | tee -a "$LOG_FILE"

# Stash any local changes
git stash

# Pull latest changes
echo "$(date): Pulling latest changes from GitHub..." | tee -a "$LOG_FILE"
git fetch origin 2>&1 | tee -a "$LOG_FILE"

# For branches, pull updates; for tags, just checkout
if [[ "$BRANCH" =~ ^v[0-9]+\.[0-9]+\.[0-9]+ ]] || git rev-parse --verify "refs/tags/$BRANCH" &>/dev/null; then
    # This is a tag, just checkout
    echo "$(date): Checking out tag $BRANCH..." | tee -a "$LOG_FILE"
    git checkout "$BRANCH" 2>&1 | tee -a "$LOG_FILE"
else
    # This is a branch, checkout and pull
    echo "$(date): Checking out and pulling branch $BRANCH..." | tee -a "$LOG_FILE"
    git checkout "$BRANCH" 2>&1 | tee -a "$LOG_FILE"
    git pull origin "$BRANCH" 2>&1 | tee -a "$LOG_FILE"
fi

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

# Health check
echo "$(date): Performing health check..." | tee -a "$LOG_FILE"
sleep 5

MAX_RETRIES=10
RETRY_COUNT=0
HEALTH_CHECK_PASSED=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8001/health 2>/dev/null || curl -f http://localhost:8001 2>/dev/null; then
        echo "$(date): ✓ Health check passed!" | tee -a "$LOG_FILE"
        HEALTH_CHECK_PASSED=true
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "$(date): Health check attempt $RETRY_COUNT failed, retrying..." | tee -a "$LOG_FILE"
    sleep 3
done

if [ "$HEALTH_CHECK_PASSED" = false ]; then
    echo "$(date): ✗ Health check failed after $MAX_RETRIES attempts!" | tee -a "$LOG_FILE"
    echo "$(date): Rolling back deployment..." | tee -a "$LOG_FILE"
    
    # Attempt to restart with previous version
    if systemctl is-active --quiet stockpredictor; then
        systemctl restart stockpredictor
    elif command -v docker-compose &> /dev/null; then
        docker-compose restart
    fi
    
    exit 1
fi

echo "$(date): ============================================" | tee -a "$LOG_FILE"
echo "$(date): Deployment to ${DEPLOYMENT_ENV} completed successfully!" | tee -a "$LOG_FILE"
echo "$(date): ============================================" | tee -a "$LOG_FILE"
