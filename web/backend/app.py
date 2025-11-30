#!/usr/bin/env python3
"""
Lazy_Bird Web API Server
=========================

Unified Flask backend for Lazy_Bird web UI.
Combines existing godot-server functionality with new web UI endpoints.

Features:
- Project management (CRUD operations)
- System status and service control
- Task queue visibility
- Test coordination (from godot-server)

Usage:
    python3 app.py [--port 5001] [--host 127.0.0.1]
"""

import os
import sys
import logging
import argparse
import atexit
from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('lazy-bird-api')

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Enable CORS for frontend development
# In production, restrict to specific origins
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://localhost:5173"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Initialize SocketIO with CORS support
socketio = SocketIO(
    app,
    cors_allowed_origins=["http://localhost:3000", "http://localhost:5173"],
    async_mode='threading',
    logger=False,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25
)


# Import and register blueprints
try:
    from api.projects import projects_bp
    from api.system import system_bp
    from api.queue import queue_bp
    from api.settings import settings_bp
    from api.issues import issues_bp
    from api.agents import agents_bp
    from api.analytics import analytics_bp

    app.register_blueprint(projects_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(queue_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(issues_bp)
    app.register_blueprint(agents_bp)
    app.register_blueprint(analytics_bp)

    logger.info("API blueprints registered successfully")

except ImportError as e:
    logger.error(f"Error importing blueprints: {e}")
    logger.error("Make sure you're running from the web/backend directory")
    sys.exit(1)


# Initialize WebSocket components
try:
    from services.websocket_manager import WebSocketManager
    from services.log_streaming import LogStreamer
    from api import websocket

    # Create instances
    ws_manager = WebSocketManager(socketio)
    log_streamer = LogStreamer(ws_manager)

    # Initialize WebSocket handlers
    websocket.init_websocket_handlers(ws_manager, log_streamer)
    websocket.register_handlers(socketio)

    # Cleanup on shutdown
    @atexit.register
    def cleanup():
        logger.info("Shutting down WebSocket services...")
        log_streamer.stop_all()

    logger.info("WebSocket server initialized successfully")

except ImportError as e:
    logger.error(f"Error initializing WebSocket: {e}")
    logger.error("Make sure Flask-SocketIO is installed")
    sys.exit(1)


@app.route('/')
def index():
    """Root endpoint"""
    return jsonify({
        'name': 'Lazy_Bird API',
        'version': '1.0.0',
        'phase': '1.1',
        'endpoints': {
            'projects': '/api/projects',
            'system': '/api/system',
            'queue': '/api/queue',
            'settings': '/api/settings',
            'issues': '/api/issues',
            'agents': '/api/agents',
            'analytics': '/api/analytics'
        },
        'websocket': {
            'enabled': True,
            'url': '/socket.io',
            'channels': ['projects', 'issues', 'agents', 'system']
        }
    })


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'lazy-bird-api'
    }), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Lazy_Bird Web API Server')
    parser.add_argument('--host', default='127.0.0.1',
                        help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000,
                        help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode')
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()

    logger.info(f"Starting Lazy_Bird Web API Server with WebSocket support")
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Debug: {args.debug}")
    logger.info(f"WebSocket: ws://{args.host}:{args.port}/socket.io")

    try:
        socketio.run(
            app,
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=False,  # Disable reloader to prevent double initialization
            log_output=args.debug,
            allow_unsafe_werkzeug=True  # Allow in development (use production WSGI in prod)
        )
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
