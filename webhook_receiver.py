#!/usr/bin/env python3
"""
GitHub Webhook Receiver for Stock Predictor Auto-Deployment

This script listens for GitHub webhook events and triggers the deployment
script when a push event is received.

Usage:
    python webhook_receiver.py [--port PORT] [--secret SECRET] [--environment ENV]

Environment Variables:
    WEBHOOK_PORT: Port to listen on (default: 9001)
    WEBHOOK_SECRET: GitHub webhook secret for verification (optional but recommended)
    DEPLOYMENT_ENV: Deployment environment (preprod or production, default: preprod)
"""

import os
import sys
import hmac
import hashlib
import subprocess
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging

# Configuration
PORT = int(os.getenv("WEBHOOK_PORT", 9001))
SECRET = os.getenv("WEBHOOK_SECRET", "")
DEPLOYMENT_ENV = os.getenv("DEPLOYMENT_ENV", "preprod")
DEPLOY_SCRIPT = "/opt/stockpredictor/deploy.sh"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/webhook-receiver.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler for GitHub webhooks"""

    def do_POST(self):
        """Handle POST requests from GitHub webhooks"""
        
        # Only accept requests to /webhook
        if self.path != "/webhook":
            self.send_response(404)
            self.end_headers()
            return

        # Read the request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        # Verify signature if secret is configured
        if SECRET:
            signature = self.headers.get('X-Hub-Signature-256', '')
            if not self.verify_signature(body, signature):
                logger.warning("Invalid webhook signature")
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'Invalid signature')
                return

        # Parse the payload
        try:
            payload = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload")
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid JSON')
            return

        # Check if it's a push event
        event_type = self.headers.get('X-GitHub-Event', '')
        if event_type == 'push':
            ref = payload.get('ref', '')
            repository = payload.get('repository', {}).get('full_name', 'unknown')
            pusher = payload.get('pusher', {}).get('name', 'unknown')
            commits = payload.get('commits', [])
            commit_count = len(commits)
            
            logger.info(f"Received push event for ref: {ref} from {pusher} ({commit_count} commits)")
            logger.info(f"Repository: {repository}")
            
            # Trigger deployment based on environment and branch
            if DEPLOYMENT_ENV == 'production':
                # Production only deploys from releases/tags, not direct pushes
                logger.info(f"Production environment ignores push events. Use releases/tags for production deployment.")
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'Production ignores push events. Use releases for production deployment.')
            elif ref in ['refs/heads/main', 'refs/heads/master']:
                # Preprod deploys from main/master branch
                logger.info(f"Triggering {DEPLOYMENT_ENV} deployment for {ref}")
                self.trigger_deployment(ref, payload)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(f'{DEPLOYMENT_ENV} deployment triggered'.encode())
            else:
                logger.info(f"Ignoring push to {ref} (not main/master)")
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'Branch ignored')
        elif event_type == 'release':
            # Handle release events for production deployment
            action = payload.get('action', '')
            release = payload.get('release', {})
            tag_name = release.get('tag_name', '')
            release_name = release.get('name', '')
            
            logger.info(f"Received release event: {action} - {release_name} ({tag_name})")
            
            if action == 'published' and DEPLOYMENT_ENV == 'production':
                logger.info(f"Triggering production deployment for release {tag_name}")
                self.trigger_deployment(f'refs/tags/{tag_name}', payload)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'Production deployment triggered')
            else:
                logger.info(f"Release event ignored (action={action}, env={DEPLOYMENT_ENV})")
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'Release event acknowledged')
        elif event_type == 'ping':
            logger.info("Received ping event")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Pong')
        else:
            logger.info(f"Received unsupported event: {event_type}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Event ignored')

    def do_GET(self):
        """Handle GET requests (health check)"""
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

    def verify_signature(self, body, signature):
        """Verify GitHub webhook signature"""
        if not signature.startswith('sha256='):
            return False
        
        expected_signature = 'sha256=' + hmac.new(
            SECRET.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)

    def trigger_deployment(self, ref, payload):
        """Execute the deployment script with context"""
        try:
            commits = payload.get('commits', [])
            commit_messages = '\n'.join([f"  - {c.get('message', 'No message')}" for c in commits[:5]])
            
            logger.info(f"Triggering deployment script for {DEPLOYMENT_ENV}...")
            logger.info(f"Ref: {ref}")
            logger.info(f"Recent commits:\n{commit_messages}")
            
            # Set environment variables for the deployment script
            env = os.environ.copy()
            env['DEPLOYMENT_ENV'] = DEPLOYMENT_ENV
            env['GIT_REF'] = ref
            
            result = subprocess.run(
                [DEPLOY_SCRIPT],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                env=env
            )
            
            if result.returncode == 0:
                logger.info(f"Deployment to {DEPLOYMENT_ENV} completed successfully")
                if result.stdout:
                    logger.info(f"Output:\n{result.stdout}")
            else:
                logger.error(f"Deployment to {DEPLOYMENT_ENV} failed with code {result.returncode}")
                if result.stderr:
                    logger.error(f"Error output:\n{result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error(f"Deployment script timed out after 5 minutes")
        except Exception as e:
            logger.error(f"Error executing deployment script: {e}")

    def log_message(self, format, *args):
        """Override to use custom logger"""
        logger.info(f"{self.address_string()} - {format % args}")


def run_server():
    """Start the webhook receiver server"""
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, WebhookHandler)
    
    logger.info("=" * 60)
    logger.info("GitHub Webhook Receiver for Stock Predictor")
    logger.info("=" * 60)
    logger.info(f"Environment: {DEPLOYMENT_ENV}")
    logger.info(f"Listening on port: {PORT}")
    logger.info(f"Secret configured: {bool(SECRET)}")
    logger.info(f"Deploy script: {DEPLOY_SCRIPT}")
    logger.info("=" * 60)
    
    if DEPLOYMENT_ENV == 'production':
        logger.warning("⚠️  PRODUCTION MODE: Only release events will trigger deployments")
    else:
        logger.info(f"ℹ️  {DEPLOYMENT_ENV.upper()} MODE: Push to main/master will trigger deployments")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down webhook receiver...")
        httpd.shutdown()


if __name__ == '__main__':
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='GitHub Webhook Receiver')
    parser.add_argument('--port', type=int, default=PORT, help='Port to listen on')
    parser.add_argument('--secret', default=SECRET, help='GitHub webhook secret')
    parser.add_argument('--environment', default=DEPLOYMENT_ENV, 
                        choices=['preprod', 'production'],
                        help='Deployment environment (preprod or production)')
    args = parser.parse_args()
    
    PORT = args.port
    if args.secret:
        SECRET = args.secret
    DEPLOYMENT_ENV = args.environment
    
    run_server()
