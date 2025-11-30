"""
WebSocket API Handlers
Handles WebSocket connections and events
"""
import logging
from flask import request
from flask_socketio import emit, disconnect
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Global instances (will be set by app.py)
websocket_manager = None
log_streamer = None


def init_websocket_handlers(ws_manager, streamer):
    """
    Initialize WebSocket handlers with manager and streamer

    Args:
        ws_manager: WebSocketManager instance
        streamer: LogStreamer instance
    """
    global websocket_manager, log_streamer
    websocket_manager = ws_manager
    log_streamer = streamer
    logger.info("WebSocket handlers initialized")


def register_handlers(socketio):
    """
    Register all WebSocket event handlers

    Args:
        socketio: Flask-SocketIO instance
    """

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        sid = request.sid
        client_data = {
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        }

        websocket_manager.register_connection(sid, client_data)

        emit('connected', {
            'status': 'connected',
            'sid': sid,
            'timestamp': websocket_manager.connections[sid]['connected_at']
        })

        logger.info(f"Client connected: {sid} from {request.remote_addr}")

    @socketio.on('disconnect')
    def handle_disconnect(*args):
        """Handle client disconnection"""
        sid = request.sid
        websocket_manager.unregister_connection(sid)
        logger.info(f"Client disconnected: {sid}")

    @socketio.on('subscribe')
    def handle_subscribe(data: Dict[str, Any]):
        """
        Handle subscription request

        Expected data:
            {
                "channels": ["projects", "issues", "agents", "system"]
            }
        """
        sid = request.sid

        if not data or 'channels' not in data:
            emit('error', {'message': 'Invalid subscribe request, missing channels'})
            return

        channels = data['channels']
        if not isinstance(channels, list):
            emit('error', {'message': 'Channels must be a list'})
            return

        # Subscribe to channels
        websocket_manager.subscribe(sid, channels)

        emit('subscribed', {
            'channels': channels,
            'timestamp': websocket_manager.connections[sid]['connected_at']
        })

        logger.info(f"Client {sid} subscribed to: {channels}")

    @socketio.on('unsubscribe')
    def handle_unsubscribe(data: Dict[str, Any]):
        """
        Handle unsubscribe request

        Expected data:
            {
                "channels": ["projects", "issues"]
            }
        """
        sid = request.sid

        if not data or 'channels' not in data:
            emit('error', {'message': 'Invalid unsubscribe request, missing channels'})
            return

        channels = data['channels']
        websocket_manager.unsubscribe(sid, channels)

        emit('unsubscribed', {'channels': channels})
        logger.info(f"Client {sid} unsubscribed from: {channels}")

    @socketio.on('subscribe_issue_logs')
    def handle_subscribe_issue_logs(data: Dict[str, Any]):
        """
        Handle issue logs subscription

        Expected data:
            {
                "issue_number": 42,
                "project_id": "test-project"
            }
        """
        sid = request.sid

        if not data or 'issue_number' not in data or 'project_id' not in data:
            emit('error', {'message': 'Invalid request, missing issue_number or project_id'})
            return

        issue_number = data['issue_number']
        project_id = data['project_id']

        # Subscribe to issue logs
        websocket_manager.subscribe_issue_logs(sid, issue_number)

        # Start streaming if not already active
        if issue_number not in log_streamer.active_streams:
            log_streamer.start_streaming(issue_number, project_id)

        emit('subscribed_issue_logs', {
            'issue_number': issue_number,
            'project_id': project_id
        })

        logger.info(f"Client {sid} subscribed to logs for issue #{issue_number}")

    @socketio.on('unsubscribe_issue_logs')
    def handle_unsubscribe_issue_logs(data: Dict[str, Any]):
        """
        Handle issue logs unsubscription

        Expected data:
            {
                "issue_number": 42
            }
        """
        sid = request.sid

        if not data or 'issue_number' not in data:
            emit('error', {'message': 'Invalid request, missing issue_number'})
            return

        issue_number = data['issue_number']
        websocket_manager.unsubscribe_issue_logs(sid, issue_number)

        # Stop streaming if no more subscribers
        if issue_number in websocket_manager.issue_log_subscriptions:
            if not websocket_manager.issue_log_subscriptions[issue_number]:
                log_streamer.stop_streaming(issue_number)

        emit('unsubscribed_issue_logs', {'issue_number': issue_number})
        logger.info(f"Client {sid} unsubscribed from logs for issue #{issue_number}")

    @socketio.on('ping')
    def handle_ping():
        """Handle ping for heartbeat"""
        emit('pong', {'timestamp': websocket_manager.connections[request.sid]['connected_at']})

    @socketio.on('get_stats')
    def handle_get_stats():
        """Get WebSocket statistics"""
        stats = websocket_manager.get_stats()
        stats['active_log_streams'] = log_streamer.get_active_streams()
        emit('stats', stats)

    @socketio.on_error_default
    def default_error_handler(e):
        """Handle errors"""
        logger.error(f"WebSocket error: {e}")
        emit('error', {'message': str(e)})


# Helper functions to broadcast events from other parts of the application

def broadcast_project_status(project_id: str, status: str, **kwargs):
    """
    Broadcast project status change

    Args:
        project_id: Project ID
        status: New status
        **kwargs: Additional data
    """
    if not websocket_manager:
        return

    data = {
        'project_id': project_id,
        'status': status,
        'timestamp': kwargs.get('timestamp'),
        **kwargs
    }

    websocket_manager.broadcast('projects', 'project.status_changed', data)


def broadcast_issue_status(issue_number: int, status: str, progress: int = None, **kwargs):
    """
    Broadcast issue status change

    Args:
        issue_number: Issue number
        status: New status
        progress: Progress percentage (0-100)
        **kwargs: Additional data
    """
    if not websocket_manager:
        return

    data = {
        'issue_number': issue_number,
        'status': status,
        'progress': progress,
        'timestamp': kwargs.get('timestamp'),
        **kwargs
    }

    websocket_manager.broadcast('issues', 'issue.status_changed', data)


def broadcast_agent_status(agent_id: str, status: str, **kwargs):
    """
    Broadcast agent status update

    Args:
        agent_id: Agent ID
        status: Agent status
        **kwargs: Additional data (cpu, memory, current_task, etc.)
    """
    if not websocket_manager:
        return

    data = {
        'agent_id': agent_id,
        'status': status,
        'timestamp': kwargs.get('timestamp'),
        **kwargs
    }

    websocket_manager.broadcast('agents', 'agent.status_updated', data)


def broadcast_system_metrics(metrics: Dict[str, Any]):
    """
    Broadcast system metrics update

    Args:
        metrics: System metrics dict
    """
    if not websocket_manager:
        return

    websocket_manager.broadcast('system', 'system.metrics_updated', metrics)
