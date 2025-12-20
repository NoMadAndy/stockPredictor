#!/bin/bash

# Stock Predictor Installation Script for Preprod/Production Servers
# This script installs and configures the Stock Predictor application on Ubuntu VMs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="/opt/stockpredictor"
DEFAULT_ENV="preprod"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "Stock Predictor Installation Script"
echo "=============================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root or with sudo${NC}"
    exit 1
fi

# Parse command line arguments
ENVIRONMENT="${1:-$DEFAULT_ENV}"

if [[ "$ENVIRONMENT" != "preprod" && "$ENVIRONMENT" != "production" ]]; then
    echo -e "${RED}ERROR: Invalid environment. Use 'preprod' or 'production'${NC}"
    echo "Usage: sudo ./install-server.sh [preprod|production]"
    exit 1
fi

echo -e "${GREEN}Installing for environment: ${ENVIRONMENT}${NC}"
echo ""

# Update system
echo "Step 1: Updating system packages..."
apt-get update
apt-get upgrade -y

# Install required packages
echo "Step 2: Installing required packages..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    nginx \
    ufw

# Clone or update repository
echo "Step 3: Setting up application directory..."
if [ -d "$APP_DIR" ]; then
    echo "Application directory exists, updating..."
    cd "$APP_DIR"
    git fetch origin
    git checkout main
    git pull origin main
else
    echo "Cloning repository..."
    git clone https://github.com/NoMadAndy/stockPredictor.git "$APP_DIR"
    cd "$APP_DIR"
fi

# Create virtual environment
echo "Step 4: Creating Python virtual environment..."
if [ ! -d "$APP_DIR/venv" ]; then
    python3 -m venv "$APP_DIR/venv"
fi

# Install Python dependencies
echo "Step 5: Installing Python dependencies..."
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

# Generate secrets
echo "Step 6: Generating secure secrets..."
SECRET_KEY=$(openssl rand -hex 32)
WEBHOOK_SECRET=$(openssl rand -hex 32)
API_KEY_ENCRYPTION_SECRET=$(openssl rand -hex 32)

echo -e "${YELLOW}Important: Save these secrets securely!${NC}"
echo "SECRET_KEY: $SECRET_KEY"
echo "WEBHOOK_SECRET: $WEBHOOK_SECRET"
echo "API_KEY_ENCRYPTION_SECRET: $API_KEY_ENCRYPTION_SECRET"
echo ""
read -p "Press Enter to continue after saving these secrets..."

# Configure systemd service for application
echo "Step 7: Configuring application service..."
cp "$APP_DIR/stockpredictor.service" /etc/systemd/system/
sed -i "s|PLEASE_CHANGE_THIS_SECRET_KEY_IN_PRODUCTION|${SECRET_KEY}|g" /etc/systemd/system/stockpredictor.service

# Add encryption secret to service
if ! grep -q "API_KEY_ENCRYPTION_SECRET" /etc/systemd/system/stockpredictor.service; then
    sed -i "/Environment=\"SECRET_KEY=/a Environment=\"API_KEY_ENCRYPTION_SECRET=${API_KEY_ENCRYPTION_SECRET}\"" /etc/systemd/system/stockpredictor.service
fi

# Set proper ownership
chown -R www-data:www-data "$APP_DIR"
chmod +x "$APP_DIR/deploy.sh"

# Configure webhook receiver service
echo "Step 8: Configuring webhook receiver service..."
cp "$APP_DIR/webhook-receiver.service" /etc/systemd/system/
sed -i "s|PLEASE_CHANGE_THIS_WEBHOOK_SECRET_IN_PRODUCTION|${WEBHOOK_SECRET}|g" /etc/systemd/system/webhook-receiver.service

# Add environment configuration to webhook receiver
if ! grep -q "DEPLOYMENT_ENV" /etc/systemd/system/webhook-receiver.service; then
    sed -i "/Environment=\"WEBHOOK_SECRET=/a Environment=\"DEPLOYMENT_ENV=${ENVIRONMENT}\"" /etc/systemd/system/webhook-receiver.service
fi

# Create log directory
mkdir -p /var/log
touch /var/log/stockpredictor.log
touch /var/log/stockpredictor-error.log
touch /var/log/stockpredictor-deploy.log
touch /var/log/webhook-receiver.log
touch /var/log/webhook-receiver-error.log
chown www-data:www-data /var/log/stockpredictor*.log
chown root:root /var/log/webhook-receiver*.log

# Enable and start services
echo "Step 9: Enabling and starting services..."
systemctl daemon-reload
systemctl enable stockpredictor
systemctl enable webhook-receiver
systemctl start stockpredictor
systemctl start webhook-receiver

# Configure firewall
echo "Step 10: Configuring firewall..."
ufw --force enable
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw allow 8001/tcp # Application
ufw allow 9001/tcp # Webhook receiver

# Configure nginx reverse proxy (optional)
echo "Step 11: Configuring Nginx reverse proxy..."
cat > /etc/nginx/sites-available/stockpredictor <<'EOF'
server {
    listen 80;
    server_name _;

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

    location /socket.io/ {
        proxy_pass http://localhost:8001/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /webhook {
        proxy_pass http://localhost:9001/webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Hub-Signature-256 $http_x_hub_signature_256;
        proxy_set_header X-GitHub-Event $http_x_github_event;
    }

    location /health {
        access_log off;
        proxy_pass http://localhost:8001/health;
    }
}
EOF

ln -sf /etc/nginx/sites-available/stockpredictor /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# Health check
echo "Step 12: Performing health check..."
sleep 5
if curl -f http://localhost:8001/health; then
    echo -e "${GREEN}✓ Application health check passed!${NC}"
else
    echo -e "${RED}✗ Application health check failed!${NC}"
    echo "Check logs with: journalctl -u stockpredictor -n 50"
    exit 1
fi

if curl -f http://localhost:9001/health; then
    echo -e "${GREEN}✓ Webhook receiver health check passed!${NC}"
else
    echo -e "${RED}✗ Webhook receiver health check failed!${NC}"
    echo "Check logs with: journalctl -u webhook-receiver -n 50"
fi

# Display summary
echo ""
echo "=============================================="
echo -e "${GREEN}Installation completed successfully!${NC}"
echo "=============================================="
echo ""
echo "Environment: ${ENVIRONMENT}"
echo "Application URL: http://$(hostname -I | awk '{print $1}'):8001"
echo "Webhook URL: http://$(hostname -I | awk '{print $1}'):9001/webhook"
echo ""
echo "Next steps:"
echo "1. Configure GitHub webhook with:"
echo "   - Payload URL: http://YOUR_SERVER:9001/webhook"
echo "   - Content type: application/json"
echo "   - Secret: ${WEBHOOK_SECRET}"
if [ "$ENVIRONMENT" = "production" ]; then
    echo "   - Events: Let me select individual events → Releases"
else
    echo "   - Events: Just the push event"
fi
echo ""
echo "2. Optional: Configure NewsAPI key in ${APP_DIR}/news_api_key.txt"
echo ""
echo "3. Monitor logs:"
echo "   - Application: journalctl -u stockpredictor -f"
echo "   - Webhook: journalctl -u webhook-receiver -f"
echo "   - Deployment: tail -f /var/log/stockpredictor-deploy.log"
echo ""
echo "4. Service commands:"
echo "   - Status: systemctl status stockpredictor"
echo "   - Restart: systemctl restart stockpredictor"
echo "   - Logs: journalctl -u stockpredictor -n 100"
echo ""
