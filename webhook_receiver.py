#!/usr/bin/env python3
"""
GitHub Webhook Receiver for Stock Predictor Auto-Deployment

This script listens for GitHub webhook events and triggers the deployment
script when a push event is received.

Usage:
    python webhook_receiver.py [--port PORT] [--secret SECRET]

Environment Variables:
    WEBHOOK_PORT: Port to listen on (default: 9001)
    WEBHOOK_SECRET: GitHub webhook secret for verification (optional but recommended)
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
            logger.info(f"Received push event for ref: {ref}")
            
            # Trigger deployment for main/master branch
            if ref in ['refs/heads/main', 'refs/heads/master']:
                self.trigger_deployment()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'Deployment triggered')
            else:
                logger.info(f"Ignoring push to {ref}")
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'Branch ignored')
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

    def trigger_deployment(self):
        """Execute the deployment script"""
        try:
            logger.info("Triggering deployment script...")
            result = subprocess.run(
                [DEPLOY_SCRIPT],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                logger.info("Deployment completed successfully")
                logger.debug(result.stdout)
            else:
                logger.error(f"Deployment failed with code {result.returncode}")
                logger.error(result.stderr)
                
        except subprocess.TimeoutExpired:
            logger.error("Deployment script timed out")
        except Exception as e:
            logger.error(f"Error executing deployment script: {e}")

    def log_message(self, format, *args):
        """Override to use custom logger"""
        logger.info(f"{self.address_string()} - {format % args}")


def run_server():
    """Start the webhook receiver server"""
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, WebhookHandler)
    
    logger.info(f"Webhook receiver listening on port {PORT}")
    logger.info(f"Secret configured: {bool(SECRET)}")
    logger.info(f"Deploy script: {DEPLOY_SCRIPT}")
    
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
    args = parser.parse_args()
    
    PORT = args.port
    if args.secret:
        SECRET = args.secret
    
    run_server()
