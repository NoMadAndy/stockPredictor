# Quick Reference - CI/CD & Deployment

## Installation

### Preprod Server
```bash
sudo wget https://raw.githubusercontent.com/NoMadAndy/stockPredictor/main/install-server.sh
sudo chmod +x install-server.sh
sudo ./install-server.sh preprod
```

### Production Server
```bash
sudo wget https://raw.githubusercontent.com/NoMadAndy/stockPredictor/main/install-server.sh
sudo chmod +x install-server.sh
sudo ./install-server.sh production
```

## GitHub Secrets (Required)

### Preprod
- `PREPROD_SERVER` - Server IP/hostname
- `PREPROD_SSH_USER` - SSH username
- `PREPROD_SSH_KEY` - SSH private key

### Production
- `PROD_SERVER` - Server IP/hostname
- `PROD_SSH_USER` - SSH username
- `PROD_SSH_KEY` - SSH private key

## Deployment

### Preprod (Automatic)
```bash
git push origin main  # Triggers automatic deployment
```

### Production (Release-based)
```bash
# Create and push tag
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0

# Then create release on GitHub
# Actions → Deploy to Production will run automatically
```

### Manual Trigger (GitHub UI)
1. Go to **Actions** tab
2. Select workflow (Deploy to Preprod/Production)
3. Click **Run workflow**
4. Fill in parameters if needed
5. Click **Run workflow** button

## Monitoring

### Check Service Status
```bash
systemctl status stockpredictor
systemctl status webhook-receiver
```

### View Logs
```bash
# Application
journalctl -u stockpredictor -f
tail -f /var/log/stockpredictor.log

# Webhook Receiver
journalctl -u webhook-receiver -f
tail -f /var/log/webhook-receiver.log

# Deployment
tail -f /var/log/stockpredictor-deploy.log
```

### Health Check
```bash
curl http://localhost:8001/health
curl http://localhost:9001/health
```

## Service Management

### Restart Services
```bash
sudo systemctl restart stockpredictor
sudo systemctl restart webhook-receiver
sudo systemctl restart nginx
```

### Stop Services
```bash
sudo systemctl stop stockpredictor
sudo systemctl stop webhook-receiver
```

### Start Services
```bash
sudo systemctl start stockpredictor
sudo systemctl start webhook-receiver
```

## Troubleshooting

### Deployment Failed
```bash
# Check deployment logs
tail -100 /var/log/stockpredictor-deploy.log

# Check application logs
journalctl -u stockpredictor -n 100

# Manual deployment
sudo /opt/stockpredictor/deploy.sh
```

### Service Won't Start
```bash
# Check service status
systemctl status stockpredictor

# Check full logs
journalctl -u stockpredictor -n 200

# Check if port is in use
sudo lsof -i :8001
```

### Webhook Not Working
```bash
# Check webhook receiver
systemctl status webhook-receiver
journalctl -u webhook-receiver -n 100

# Test webhook endpoint
curl http://localhost:9001/health

# Check firewall
sudo ufw status | grep 9001
```

## Rollback

### Automatic
Health checks automatically trigger rollback on failure.

### Manual
```bash
cd /opt/stockpredictor
sudo git checkout v1.0.0  # or previous tag
sudo /opt/stockpredictor/deploy.sh
```

## GitHub Webhook Setup

### Preprod Webhook
- URL: `http://PREPROD_SERVER:9001/webhook`
- Content type: `application/json`
- Secret: Use `WEBHOOK_SECRET` from server
- Events: **Just the push event**

### Production Webhook
- URL: `http://PROD_SERVER:9001/webhook`
- Content type: `application/json`
- Secret: Use `WEBHOOK_SECRET` from server
- Events: **Releases** (Let me select → Releases)

## Useful Commands

### View Running Processes
```bash
ps aux | grep python
ps aux | grep stockpredictor
```

### Check Port Usage
```bash
sudo netstat -tulpn | grep 8001
sudo netstat -tulpn | grep 9001
```

### Git Status on Server
```bash
cd /opt/stockpredictor
git status
git log -5 --oneline
git branch -a
```

### Disk Space
```bash
df -h /opt/stockpredictor
du -sh /opt/stockpredictor
```

### System Resources
```bash
free -h
top -bn1 | head -20
```

## Emergency Procedures

### Application Crashed
```bash
sudo systemctl restart stockpredictor
journalctl -u stockpredictor -n 100
```

### Out of Disk Space
```bash
# Clean old logs
sudo journalctl --vacuum-time=7d
sudo find /var/log -name "*.log" -mtime +30 -delete

# Clean old deployments (if backups enabled)
sudo find /opt -name "stockpredictor-backup-*" -mtime +7 -delete
```

### Nginx Issues
```bash
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
tail -f /var/log/nginx/error.log
```

## Documentation

- **Full Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Installation**: [INSTALLATION.md](INSTALLATION.md)
- **General Info**: [README.md](README.md)

## Support

For issues or questions:
1. Check logs first
2. Review documentation
3. Search GitHub Issues
4. Create new issue with logs and details
