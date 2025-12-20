# GitHub Actions Setup Guide

This guide helps you configure GitHub Actions for automated deployments.

## Prerequisites

1. Two Ubuntu servers (Preprod and Production)
2. SSH access to both servers
3. GitHub repository with admin access

## Step 1: Install on Servers

### Preprod Server

```bash
# SSH to preprod server
ssh user@preprod-server

# Download and run installation script
sudo wget https://raw.githubusercontent.com/NoMadAndy/stockPredictor/main/install-server.sh
sudo chmod +x install-server.sh
sudo ./install-server.sh preprod

# Save the generated secrets shown at the end!
```

### Production Server

```bash
# SSH to production server
ssh user@prod-server

# Download and run installation script
sudo wget https://raw.githubusercontent.com/NoMadAndy/stockPredictor/main/install-server.sh
sudo chmod +x install-server.sh
sudo ./install-server.sh production

# Save the generated secrets shown at the end!
```

## Step 2: Generate SSH Deploy Keys

On your local machine:

```bash
# Generate SSH key pair for deployments
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy_key_preprod
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy_key_prod

# Copy public keys to servers
ssh-copy-id -i ~/.ssh/github_deploy_key_preprod.pub user@preprod-server
ssh-copy-id -i ~/.ssh/github_deploy_key_prod.pub user@prod-server

# Test the connections
ssh -i ~/.ssh/github_deploy_key_preprod user@preprod-server "echo 'Preprod connection works'"
ssh -i ~/.ssh/github_deploy_key_prod user@prod-server "echo 'Production connection works'"
```

## Step 3: Configure GitHub Secrets

Go to your repository on GitHub:
**Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets:

### Preprod Secrets

| Secret Name | Value | Example |
|------------|--------|---------|
| `PREPROD_SERVER` | Preprod server IP or hostname | `192.168.1.100` or `preprod.example.com` |
| `PREPROD_SSH_USER` | SSH username | `ubuntu` or `root` |
| `PREPROD_SSH_KEY` | Contents of `~/.ssh/github_deploy_key_preprod` | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `PREPROD_SSH_PORT` | SSH port (optional) | `22` (default if not set) |

### Production Secrets

| Secret Name | Value | Example |
|------------|--------|---------|
| `PROD_SERVER` | Production server IP or hostname | `192.168.1.200` or `prod.example.com` |
| `PROD_SSH_USER` | SSH username | `ubuntu` or `root` |
| `PROD_SSH_KEY` | Contents of `~/.ssh/github_deploy_key_prod` | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `PROD_SSH_PORT` | SSH port (optional) | `22` (default if not set) |

### How to add a secret:

1. Click **New repository secret**
2. Enter the name (e.g., `PREPROD_SERVER`)
3. Paste the value
4. Click **Add secret**
5. Repeat for all secrets

## Step 4: Configure GitHub Environments (Optional but Recommended)

GitHub Environments add protection rules for deployments.

### Create Preprod Environment

1. Go to **Settings** → **Environments**
2. Click **New environment**
3. Name: `preprod`
4. Click **Configure environment**
5. (Optional) Add environment secrets if different from repository secrets
6. Click **Save protection rules**

### Create Production Environment with Protection

1. Go to **Settings** → **Environments**
2. Click **New environment**
3. Name: `production`
4. Click **Configure environment**
5. Enable **Required reviewers**
   - Add yourself or team members who must approve production deployments
6. (Optional) Enable **Wait timer** - Delay deployments by X minutes
7. (Optional) Add **Deployment branches** rule to only allow specific branches
8. Click **Save protection rules**

## Step 5: Configure GitHub Webhooks (Optional)

Webhooks provide an additional deployment trigger independent of GitHub Actions.

### Preprod Webhook

1. Go to **Settings** → **Webhooks** → **Add webhook**
2. Configure:
   - **Payload URL**: `http://PREPROD_SERVER_IP:9001/webhook`
   - **Content type**: `application/json`
   - **Secret**: Use the `WEBHOOK_SECRET` from preprod server installation
   - **SSL verification**: Disable if using HTTP (enable for HTTPS)
   - **Events**: Select **Just the push event**
   - **Active**: ✓
3. Click **Add webhook**
4. Test with **Redeliver** on the Recent Deliveries tab

### Production Webhook

1. Go to **Settings** → **Webhooks** → **Add webhook**
2. Configure:
   - **Payload URL**: `http://PROD_SERVER_IP:9001/webhook`
   - **Content type**: `application/json`
   - **Secret**: Use the `WEBHOOK_SECRET` from production server installation
   - **SSL verification**: Disable if using HTTP (enable for HTTPS)
   - **Events**: Select **Let me select individual events** → Check **Releases**
   - **Active**: ✓
3. Click **Add webhook**

## Step 6: Test the Setup

### Test CI Workflow

```bash
# Create a test branch
git checkout -b test-ci

# Make a small change
echo "# Test" >> README.md
git add README.md
git commit -m "Test CI workflow"
git push origin test-ci

# Create a pull request on GitHub
# Watch Actions tab to see CI workflow run
```

### Test Preprod Deployment

```bash
# Merge to main or push directly
git checkout main
git pull origin main
git merge test-ci
git push origin main

# Watch Actions tab to see "Deploy to Preprod" workflow
# Check preprod server: curl http://preprod-server:8001/health
```

### Test Production Deployment

```bash
# Create a release tag
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# On GitHub: Go to Releases → Draft a new release
# - Choose tag: v1.0.0
# - Release title: Version 1.0.0
# - Description: Initial production release
# - Click "Publish release"

# Watch Actions tab to see "Deploy to Production" workflow
# Approve deployment if environment protection is enabled
# Check production server: curl http://prod-server:8001/health
```

## Troubleshooting

### SSH Connection Fails in GitHub Actions

**Error**: `Permission denied (publickey)`

**Solution**:
```bash
# Verify public key is on server
ssh user@server "cat ~/.ssh/authorized_keys"

# Verify private key matches
ssh-keygen -y -f ~/.ssh/github_deploy_key_preprod
# Compare output with authorized_keys on server

# Check key permissions on server
ssh user@server "chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"

# Verify GitHub secret contains full private key including headers
# -----BEGIN OPENSSH PRIVATE KEY-----
# ...
# -----END OPENSSH PRIVATE KEY-----
```

### Health Check Fails

**Error**: `curl: (7) Failed to connect`

**Solution**:
```bash
# On server, check if application is running
systemctl status stockpredictor

# Check if port is listening
sudo netstat -tulpn | grep 8001

# Check application logs
journalctl -u stockpredictor -n 50

# Check firewall
sudo ufw status
```

### Webhook Returns 401 Unauthorized

**Error**: `Invalid webhook signature`

**Solution**:
```bash
# Verify webhook secret matches between GitHub and server
# On server:
grep WEBHOOK_SECRET /etc/systemd/system/webhook-receiver.service

# Update GitHub webhook with correct secret
# Settings → Webhooks → Edit → Update secret
```

### Deployment Script Fails

**Error**: `deploy.sh: permission denied`

**Solution**:
```bash
# On server, make script executable
sudo chmod +x /opt/stockpredictor/deploy.sh

# Verify ownership
sudo chown -R www-data:www-data /opt/stockpredictor

# Test manual deployment
sudo /opt/stockpredictor/deploy.sh
```

## Verification Checklist

After setup, verify:

- [ ] CI workflow runs on push/PR
- [ ] Preprod deployment runs on push to main
- [ ] Production deployment runs on release
- [ ] SSH connections work from GitHub Actions
- [ ] Health checks pass after deployment
- [ ] Webhook endpoint responds (if configured)
- [ ] Services restart automatically
- [ ] Logs are accessible and informative

## Security Best Practices

1. **Rotate SSH keys regularly** (every 90 days)
2. **Use strong webhook secrets** (32+ characters)
3. **Enable branch protection** on main branch
4. **Require PR reviews** before merging to main
5. **Use environment protection** for production
6. **Monitor deployment logs** regularly
7. **Test rollback procedures** periodically
8. **Keep secrets in GitHub Secrets**, never in code
9. **Use separate keys** for each environment
10. **Enable 2FA** on GitHub account

## Monitoring

### GitHub Actions

- View workflow runs: **Actions** tab
- Download logs: Click on workflow run → Download logs
- Re-run failed workflows: Click **Re-run jobs**

### Server Monitoring

```bash
# Application status
systemctl status stockpredictor

# Recent deployments
tail -50 /var/log/stockpredictor-deploy.log

# Application logs
journalctl -u stockpredictor -n 100 --since "1 hour ago"

# Webhook receiver logs
journalctl -u webhook-receiver -n 100 --since "1 hour ago"
```

## Support

If you encounter issues:

1. Check logs first (GitHub Actions + Server logs)
2. Review this guide and [DEPLOYMENT.md](DEPLOYMENT.md)
3. Search existing GitHub Issues
4. Create a new issue with:
   - Environment (preprod/production)
   - Error messages and logs
   - Steps to reproduce
   - What you've already tried

## Next Steps

Once setup is complete:

1. Configure SSL/TLS certificates (Let's Encrypt recommended)
2. Set up monitoring/alerting (optional)
3. Configure backup strategy
4. Document your specific deployment procedures
5. Train team members on deployment process
