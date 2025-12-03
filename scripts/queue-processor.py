#!/usr/bin/env python3
"""
Lazy_Bird Queue Processor Service
Monitors task queue and spawns agent-runner.sh processes for queued tasks
Phase 1.1: Multi-project support with concurrent agent management
"""

import time
import sys
import json
import logging
import subprocess
import signal
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("queue-processor")


class AgentProcess:
    """Represents a running agent process"""

    def __init__(self, task_id: str, project_id: str, issue_number: int, process: subprocess.Popen, task_file: Path):
        self.task_id = task_id
        self.project_id = project_id
        self.issue_number = issue_number
        self.process = process
        self.task_file = task_file
        self.started_at = datetime.now()

    def is_running(self) -> bool:
        """Check if process is still running"""
        return self.process.poll() is None

    def get_exit_code(self) -> Optional[int]:
        """Get process exit code if finished"""
        return self.process.poll()


class QueueProcessor:
    """Monitors task queue and spawns agent runners"""

    def __init__(self):
        """Initialize queue processor"""
        self.config_file = Path.home() / ".config" / "lazy_birtd" / "config.yml"
        self.queue_dir = Path.home() / ".config" / "lazy_birtd" / "queue"
        self.log_dir = Path.home() / ".config" / "lazy_birtd" / "logs"
        self.scripts_dir = Path(__file__).parent

        # Load configuration
        self.config = self.load_config()
        self.max_concurrent_agents = self.config.get("max_concurrent_agents", 1)
        self.poll_interval = self.config.get("poll_interval_seconds", 30)

        # Active agent processes
        self.active_agents: Dict[str, AgentProcess] = {}

        # Shutdown flag
        self.shutdown_requested = False

        # Create directories if needed
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Queue Processor initialized")
        logger.info(f"  Queue directory: {self.queue_dir}")
        logger.info(f"  Max concurrent agents: {self.max_concurrent_agents}")
        logger.info(f"  Poll interval: {self.poll_interval}s")

    def load_config(self) -> Dict:
        """Load configuration from YAML file"""
        if not self.config_file.exists():
            logger.error(f"Configuration file not found: {self.config_file}")
            raise FileNotFoundError(f"Config not found: {self.config_file}")

        try:
            with open(self.config_file, "r") as f:
                config = yaml.safe_load(f)
                return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def get_task_status(self, task_file: Path) -> Optional[str]:
        """Read task status from JSON file"""
        try:
            with open(task_file, "r") as f:
                task_data = json.load(f)
                # Default to "queued" for tasks without status (newly created by issue-watcher)
                return task_data.get("status", "queued")
        except Exception as e:
            logger.error(f"Failed to read task file {task_file}: {e}")
            return None

    def update_task_status(self, task_file: Path, status: str, agent_pid: Optional[int] = None):
        """Update task status in JSON file"""
        try:
            with open(task_file, "r") as f:
                task_data = json.load(f)

            task_data["status"] = status
            task_data["_last_updated"] = datetime.now().isoformat()

            if agent_pid:
                task_data["_agent_pid"] = agent_pid

            if status == "processing":
                task_data["_processing_started_at"] = datetime.now().isoformat()
            elif status in ["completed", "failed"]:
                task_data["completed_at"] = datetime.now().isoformat()

            with open(task_file, "w") as f:
                json.dump(task_data, f, indent=2)

            logger.info(f"Updated task {task_file.stem} status: {status}")
        except Exception as e:
            logger.error(f"Failed to update task file {task_file}: {e}")

    def find_queued_tasks(self) -> List[Path]:
        """Find all queued task files"""
        queued_tasks = []

        for task_file in self.queue_dir.glob("task-*.json"):
            status = self.get_task_status(task_file)
            if status == "queued":
                queued_tasks.append(task_file)

        return sorted(queued_tasks, key=lambda p: p.stat().st_mtime)

    def spawn_agent(self, task_file: Path) -> Optional[AgentProcess]:
        """Spawn agent-runner.sh process for a task"""
        try:
            # Parse task file to get metadata
            with open(task_file, "r") as f:
                task_data = json.load(f)

            task_id = task_data.get("task_id", task_file.stem)
            project_id = task_data.get("project_id", "unknown")
            issue_number = task_data.get("issue_id", 0)

            # Path to agent-runner.sh
            agent_runner = self.scripts_dir / "agent-runner.sh"
            if not agent_runner.exists():
                logger.error(f"agent-runner.sh not found at {agent_runner}")
                return None

            # Prepare log file
            log_file = self.log_dir / f"{task_id}.log"

            logger.info(f"Spawning agent for task {task_id} (Issue #{issue_number}, Project: {project_id})")

            # Spawn agent-runner.sh as subprocess
            with open(log_file, "w") as log:
                process = subprocess.Popen(
                    [str(agent_runner), str(task_file)],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,  # Detach from parent
                )

            # Update task status to processing
            self.update_task_status(task_file, "processing", agent_pid=process.pid)

            # Create AgentProcess object
            agent = AgentProcess(task_id, project_id, issue_number, process, task_file)

            logger.info(f"Agent spawned: PID {process.pid}, Log: {log_file}")
            return agent

        except Exception as e:
            logger.error(f"Failed to spawn agent for {task_file}: {e}")
            self.update_task_status(task_file, "failed")
            return None

    def cleanup_finished_agents(self):
        """Check for finished agents and clean them up"""
        finished_task_ids = []

        for task_id, agent in self.active_agents.items():
            if not agent.is_running():
                exit_code = agent.get_exit_code()

                if exit_code == 0:
                    logger.info(f"Agent completed successfully: {task_id} (PID {agent.process.pid})")
                    self.update_task_status(agent.task_file, "completed")
                else:
                    logger.error(f"Agent failed: {task_id} (PID {agent.process.pid}, Exit code: {exit_code})")
                    self.update_task_status(agent.task_file, "failed")

                finished_task_ids.append(task_id)

        # Remove finished agents
        for task_id in finished_task_ids:
            del self.active_agents[task_id]

    def available_agent_slots(self) -> int:
        """Calculate how many more agents can be spawned"""
        return self.max_concurrent_agents - len(self.active_agents)

    def process_queue(self):
        """Main queue processing logic - one iteration"""
        # Clean up finished agents
        self.cleanup_finished_agents()

        # Check if we can spawn more agents
        available_slots = self.available_agent_slots()
        if available_slots <= 0:
            return

        # Find queued tasks
        queued_tasks = self.find_queued_tasks()

        if not queued_tasks:
            return

        logger.info(f"Found {len(queued_tasks)} queued task(s), {available_slots} agent slot(s) available")

        # Spawn agents for queued tasks
        spawned = 0
        for task_file in queued_tasks:
            if spawned >= available_slots:
                break

            # Check if already processing (race condition protection)
            task_id = task_file.stem
            if task_id in self.active_agents:
                continue

            agent = self.spawn_agent(task_file)
            if agent:
                self.active_agents[task_id] = agent
                spawned += 1

    def run(self):
        """Main service loop"""
        logger.info("🚀 Queue Processor started")
        logger.info(f"   Max concurrent agents: {self.max_concurrent_agents}")
        logger.info(f"   Polling every {self.poll_interval} seconds")
        logger.info(f"   Press Ctrl+C to stop")
        logger.info("")

        # Setup signal handlers
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

        while not self.shutdown_requested:
            try:
                self.process_queue()
                time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(self.poll_interval)

        logger.info("Shutting down...")
        self.shutdown()

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown_requested = True

    def shutdown(self):
        """Graceful shutdown - wait for agents or kill them"""
        if not self.active_agents:
            logger.info("No active agents, exiting")
            return

        logger.info(f"Waiting for {len(self.active_agents)} active agent(s) to finish...")
        logger.info("Press Ctrl+C again to force kill")

        try:
            # Wait up to 30 seconds for agents to finish
            wait_time = 0
            while self.active_agents and wait_time < 30:
                self.cleanup_finished_agents()
                time.sleep(1)
                wait_time += 1

            # Force kill remaining agents
            if self.active_agents:
                logger.warning(f"Force killing {len(self.active_agents)} remaining agent(s)")
                for task_id, agent in self.active_agents.items():
                    try:
                        agent.process.terminate()
                        logger.info(f"Terminated agent: {task_id} (PID {agent.process.pid})")
                    except Exception as e:
                        logger.error(f"Failed to terminate agent {task_id}: {e}")

        except KeyboardInterrupt:
            logger.warning("Force shutdown requested")
            for task_id, agent in self.active_agents.items():
                try:
                    agent.process.kill()
                except:
                    pass

        logger.info("Queue Processor stopped")


def main():
    """Entry point"""
    try:
        processor = QueueProcessor()
        processor.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
