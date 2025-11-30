"""
Log Streaming Service
Watches log files and streams updates in real-time via WebSocket
"""
import os
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
from threading import Thread, Event
from datetime import datetime

logger = logging.getLogger(__name__)


class LogStreamer:
    """Streams log file updates in real-time"""

    def __init__(self, websocket_manager, log_dir: Optional[Path] = None):
        """
        Initialize log streamer

        Args:
            websocket_manager: WebSocketManager instance
            log_dir: Path to log directory
        """
        self.websocket_manager = websocket_manager
        self.log_dir = log_dir or Path.home() / '.config' / 'lazy_birtd' / 'logs'
        self.active_streams: Dict[int, Dict[str, Any]] = {}  # issue_number -> stream info
        self.stop_event = Event()
        self.poll_interval = 0.5  # Poll every 500ms

    def start_streaming(self, issue_number: int, project_id: str):
        """
        Start streaming logs for an issue

        Args:
            issue_number: Issue number
            project_id: Project ID
        """
        if issue_number in self.active_streams:
            logger.warning(f"Log streaming already active for issue #{issue_number}")
            return

        # Find log file
        log_file = self._find_log_file(project_id, issue_number)
        if not log_file or not log_file.exists():
            logger.warning(f"Log file not found for issue #{issue_number}")
            return

        # Start streaming thread
        stream_info = {
            'log_file': log_file,
            'position': log_file.stat().st_size if log_file.exists() else 0,
            'thread': None
        }

        thread = Thread(
            target=self._stream_loop,
            args=(issue_number, stream_info),
            daemon=True,
            name=f"log-stream-{issue_number}"
        )
        stream_info['thread'] = thread
        self.active_streams[issue_number] = stream_info

        thread.start()
        logger.info(f"Started log streaming for issue #{issue_number}")

    def stop_streaming(self, issue_number: int):
        """
        Stop streaming logs for an issue

        Args:
            issue_number: Issue number
        """
        if issue_number in self.active_streams:
            del self.active_streams[issue_number]
            logger.info(f"Stopped log streaming for issue #{issue_number}")

    def stop_all(self):
        """Stop all log streaming"""
        self.stop_event.set()
        self.active_streams.clear()
        logger.info("Stopped all log streaming")

    def _stream_loop(self, issue_number: int, stream_info: Dict[str, Any]):
        """
        Main streaming loop for a log file

        Args:
            issue_number: Issue number
            stream_info: Stream information dict
        """
        log_file = stream_info['log_file']
        position = stream_info['position']

        try:
            with open(log_file, 'r') as f:
                # Seek to last position
                f.seek(position)

                while not self.stop_event.is_set() and issue_number in self.active_streams:
                    # Read new lines
                    line = f.readline()

                    if line:
                        # Parse and broadcast log entry
                        log_entry = self._parse_log_line(line, issue_number)
                        if log_entry:
                            self.websocket_manager.broadcast_issue_log(issue_number, log_entry)

                        # Update position
                        stream_info['position'] = f.tell()
                    else:
                        # No new data, wait before checking again
                        time.sleep(self.poll_interval)

                        # Check if file was rotated or deleted
                        if not log_file.exists():
                            logger.warning(f"Log file disappeared for issue #{issue_number}")
                            break

                        # Update file size in case it shrank (rotation)
                        current_size = log_file.stat().st_size
                        if current_size < stream_info['position']:
                            logger.info(f"Log file rotated for issue #{issue_number}, resetting position")
                            f.seek(0)
                            stream_info['position'] = 0

        except Exception as e:
            logger.error(f"Error streaming logs for issue #{issue_number}: {e}")
        finally:
            # Clean up
            if issue_number in self.active_streams:
                del self.active_streams[issue_number]

    def _find_log_file(self, project_id: str, issue_number: int) -> Optional[Path]:
        """
        Find log file for issue

        Args:
            project_id: Project ID
            issue_number: Issue number

        Returns:
            Path to log file or None
        """
        # Pattern: agent-{project_id}-task-{issue_number}.log
        log_file = self.log_dir / f"agent-{project_id}-task-{issue_number}.log"

        if log_file.exists():
            return log_file

        # Try alternative patterns
        patterns = [
            f"agent-{project_id}-issue-{issue_number}.log",
            f"{project_id}-task-{issue_number}.log",
            f"task-{issue_number}.log",
        ]

        for pattern in patterns:
            alt_file = self.log_dir / pattern
            if alt_file.exists():
                return alt_file

        return None

    def _parse_log_line(self, line: str, issue_number: int) -> Optional[Dict[str, Any]]:
        """
        Parse log line into structured format

        Args:
            line: Raw log line
            issue_number: Issue number

        Returns:
            Parsed log entry or None
        """
        line = line.strip()
        if not line:
            return None

        # Determine log level
        level = 'info'
        if 'ERROR' in line or 'error' in line.lower():
            level = 'error'
        elif 'WARNING' in line or 'warning' in line.lower():
            level = 'warning'
        elif 'DEBUG' in line:
            level = 'debug'

        # Determine source
        source = 'console'
        if 'claude' in line.lower() or 'agent' in line.lower():
            source = 'claude'
        elif 'test' in line.lower():
            source = 'test'

        return {
            'issue_number': issue_number,
            'source': source,
            'message': line,
            'level': level,
            'timestamp': datetime.now().isoformat()
        }

    def get_active_streams(self) -> Dict[int, str]:
        """
        Get currently active streams

        Returns:
            Dict mapping issue_number to log file path
        """
        return {
            issue_number: str(info['log_file'])
            for issue_number, info in self.active_streams.items()
        }
