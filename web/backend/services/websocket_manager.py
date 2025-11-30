"""
WebSocket Manager Service
Manages WebSocket connections, subscriptions, and event broadcasting
"""
import logging
from typing import Dict, Set, Any, Optional
from datetime import datetime
from flask_socketio import SocketIO, join_room, leave_room, emit

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and subscriptions"""

    def __init__(self, socketio: SocketIO):
        """
        Initialize WebSocket manager

        Args:
            socketio: Flask-SocketIO instance
        """
        self.socketio = socketio
        self.connections: Dict[str, Dict[str, Any]] = {}  # sid -> connection info
        self.subscriptions: Dict[str, Set[str]] = {  # channel -> set of sids
            'projects': set(),
            'issues': set(),
            'agents': set(),
            'system': set(),
        }
        self.issue_log_subscriptions: Dict[int, Set[str]] = {}  # issue_number -> set of sids

    def register_connection(self, sid: str, data: Optional[Dict] = None):
        """
        Register a new WebSocket connection

        Args:
            sid: Socket ID
            data: Optional connection data
        """
        self.connections[sid] = {
            'connected_at': datetime.now().isoformat(),
            'subscriptions': set(),
            'data': data or {}
        }
        logger.info(f"WebSocket connection registered: {sid}")

    def unregister_connection(self, sid: str):
        """
        Unregister a WebSocket connection

        Args:
            sid: Socket ID
        """
        if sid in self.connections:
            # Remove from all subscriptions
            for channel in list(self.connections[sid]['subscriptions']):
                self.unsubscribe(sid, channel)

            # Remove from issue log subscriptions
            for issue_number, sids in list(self.issue_log_subscriptions.items()):
                if sid in sids:
                    sids.remove(sid)
                    if not sids:
                        del self.issue_log_subscriptions[issue_number]

            del self.connections[sid]
            logger.info(f"WebSocket connection unregistered: {sid}")

    def subscribe(self, sid: str, channels: list):
        """
        Subscribe connection to channels

        Args:
            sid: Socket ID
            channels: List of channel names
        """
        if sid not in self.connections:
            logger.warning(f"Attempted to subscribe unknown connection: {sid}")
            return

        for channel in channels:
            if channel in self.subscriptions:
                self.subscriptions[channel].add(sid)
                self.connections[sid]['subscriptions'].add(channel)
                join_room(channel, sid=sid)
                logger.info(f"Connection {sid} subscribed to {channel}")

    def unsubscribe(self, sid: str, channels: list):
        """
        Unsubscribe connection from channels

        Args:
            sid: Socket ID
            channels: List of channel names
        """
        if sid not in self.connections:
            return

        for channel in channels:
            if channel in self.subscriptions and sid in self.subscriptions[channel]:
                self.subscriptions[channel].remove(sid)
                self.connections[sid]['subscriptions'].discard(channel)
                leave_room(channel, sid=sid)
                logger.info(f"Connection {sid} unsubscribed from {channel}")

    def subscribe_issue_logs(self, sid: str, issue_number: int):
        """
        Subscribe to logs for a specific issue

        Args:
            sid: Socket ID
            issue_number: Issue number
        """
        if sid not in self.connections:
            return

        if issue_number not in self.issue_log_subscriptions:
            self.issue_log_subscriptions[issue_number] = set()

        self.issue_log_subscriptions[issue_number].add(sid)
        room = f"issue_logs_{issue_number}"
        join_room(room, sid=sid)
        logger.info(f"Connection {sid} subscribed to logs for issue #{issue_number}")

    def unsubscribe_issue_logs(self, sid: str, issue_number: int):
        """
        Unsubscribe from logs for a specific issue

        Args:
            sid: Socket ID
            issue_number: Issue number
        """
        if issue_number in self.issue_log_subscriptions:
            self.issue_log_subscriptions[issue_number].discard(sid)
            if not self.issue_log_subscriptions[issue_number]:
                del self.issue_log_subscriptions[issue_number]

            room = f"issue_logs_{issue_number}"
            leave_room(room, sid=sid)
            logger.info(f"Connection {sid} unsubscribed from logs for issue #{issue_number}")

    def broadcast(self, channel: str, event: str, data: Dict[str, Any]):
        """
        Broadcast event to all subscribers of a channel

        Args:
            channel: Channel name
            event: Event type
            data: Event data
        """
        if channel not in self.subscriptions:
            logger.warning(f"Attempted to broadcast to unknown channel: {channel}")
            return

        subscriber_count = len(self.subscriptions[channel])
        if subscriber_count > 0:
            self.socketio.emit(event, data, room=channel)
            logger.debug(f"Broadcasted {event} to {subscriber_count} subscribers on {channel}")

    def broadcast_issue_log(self, issue_number: int, log_data: Dict[str, Any]):
        """
        Broadcast log entry to issue log subscribers

        Args:
            issue_number: Issue number
            log_data: Log entry data
        """
        room = f"issue_logs_{issue_number}"
        subscriber_count = len(self.issue_log_subscriptions.get(issue_number, set()))

        if subscriber_count > 0:
            self.socketio.emit('log.new_entry', log_data, room=room)
            logger.debug(f"Broadcasted log entry for issue #{issue_number} to {subscriber_count} subscribers")

    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.connections)

    def get_channel_subscribers(self, channel: str) -> int:
        """Get number of subscribers for a channel"""
        return len(self.subscriptions.get(channel, set()))

    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket statistics"""
        return {
            'total_connections': self.get_connection_count(),
            'channels': {
                channel: len(sids)
                for channel, sids in self.subscriptions.items()
            },
            'issue_log_subscriptions': len(self.issue_log_subscriptions)
        }
