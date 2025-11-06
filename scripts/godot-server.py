#!/usr/bin/env python3
"""
Godot Server - Test Coordination Service
========================================

HTTP API server that queues and executes Godot tests sequentially,
allowing multiple Claude Code agents to coordinate test execution safely.

Features:
- REST API for test submission and status checking
- Sequential test execution (one at a time)
- Job queue management with priorities
- Test result parsing (gdUnit4, GUT)
- Timeout enforcement
- Resource monitoring
- Artifact storage

Usage:
    python3 godot-server.py [--port 5000] [--host 127.0.0.1]

API Endpoints:
    POST   /test/submit        - Submit new test job
    GET    /test/status/<id>   - Check job status
    GET    /test/results/<id>  - Get detailed results
    DELETE /test/cancel/<id>   - Cancel queued/running job
    GET    /health             - Health check
    GET    /queue              - View current queue
"""

import os
import sys
import json
import time
import uuid
import subprocess
import threading
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Any
from queue import Queue, Empty
from pathlib import Path

try:
    from flask import Flask, request, jsonify, send_file
    import psutil
except ImportError:
    print("Error: Required packages not installed")
    print("Install: pip3 install flask psutil")
    sys.exit(1)

# Configuration
# Default artifacts directory (can be overridden by env var or command line)
DEFAULT_ARTIFACTS_DIR = os.environ.get('LAZY_BIRD_ARTIFACTS_DIR',
                                        str(Path.home() / '.local/share/lazy_birtd/tests'))
MAX_QUEUE_SIZE = 50
DEFAULT_TIMEOUT = 300  # 5 minutes
JOB_RETENTION_DAYS = 7

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('godot-server')

# Flask app
app = Flask(__name__)


class JobStatus(Enum):
    """Job lifecycle states"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class Priority(Enum):
    """Job priority levels"""
    HIGH = 1    # Retry attempts, critical fixes
    NORMAL = 2  # Regular tasks
    LOW = 3     # Non-blocking refactors


@dataclass
class TestJob:
    """Test job specification"""
    job_id: str
    project_path: str
    test_suite: str = "all"
    framework: str = "gdUnit4"
    timeout_seconds: int = DEFAULT_TIMEOUT
    agent_id: Optional[str] = None
    task_id: Optional[int] = None
    callback_url: Optional[str] = None
    priority: Priority = Priority.NORMAL

    # Status tracking
    status: JobStatus = JobStatus.QUEUED
    submitted_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    result: Optional[str] = None  # "passed" or "failed"
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    output: str = ""
    error_message: str = ""

    # Artifacts
    log_path: Optional[str] = None
    junit_path: Optional[str] = None


@dataclass
class TestSummary:
    """Test execution summary"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0


class JobQueue:
    """Thread-safe job queue with priority support"""

    def __init__(self, maxsize: int = MAX_QUEUE_SIZE):
        self.queue = Queue(maxsize=maxsize)
        self.jobs: Dict[str, TestJob] = {}
        self.active_job: Optional[TestJob] = None
        self.lock = threading.Lock()

    def submit(self, job: TestJob) -> bool:
        """Submit a new job to the queue"""
        try:
            with self.lock:
                if len(self.jobs) >= MAX_QUEUE_SIZE:
                    return False

                job.submitted_at = datetime.now()
                self.jobs[job.job_id] = job
                self.queue.put(job, block=False)
                logger.info(f"Job {job.job_id} submitted (task #{job.task_id})")
                return True
        except Exception as e:
            logger.error(f"Failed to submit job: {e}")
            return False

    def get_next(self, timeout: float = 1.0) -> Optional[TestJob]:
        """Get next job from queue (blocking with timeout)"""
        try:
            job = self.queue.get(timeout=timeout)
            with self.lock:
                self.active_job = job
            return job
        except Empty:
            return None

    def get_job(self, job_id: str) -> Optional[TestJob]:
        """Get job by ID"""
        with self.lock:
            return self.jobs.get(job_id)

    def update_job(self, job: TestJob):
        """Update job in registry"""
        with self.lock:
            self.jobs[job.job_id] = job

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued or running job"""
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return False

            if job.status == JobStatus.QUEUED:
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now()
                return True

            # Cannot cancel running jobs (would require process tracking)
            return False

    def get_queue_position(self, job_id: str) -> int:
        """Get position in queue (1-indexed)"""
        with self.lock:
            queued_jobs = [j for j in self.jobs.values()
                          if j.status == JobStatus.QUEUED]
            queued_jobs.sort(key=lambda j: j.submitted_at)

            for i, job in enumerate(queued_jobs, 1):
                if job.job_id == job_id:
                    return i
            return 0

    def get_queue_depth(self) -> int:
        """Get number of queued jobs"""
        with self.lock:
            return sum(1 for j in self.jobs.values()
                      if j.status == JobStatus.QUEUED)

    def cleanup_old_jobs(self, days: int = JOB_RETENTION_DAYS):
        """Remove jobs older than specified days"""
        cutoff = datetime.now() - timedelta(days=days)
        with self.lock:
            old_jobs = [jid for jid, job in self.jobs.items()
                       if job.completed_at and job.completed_at < cutoff]
            for jid in old_jobs:
                del self.jobs[jid]
                logger.info(f"Cleaned up old job {jid}")


class TestExecutor:
    """Executes Godot tests and parses results"""

    def __init__(self, artifacts_dir: Path):
        self.artifacts_dir = artifacts_dir
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.current_process: Optional[subprocess.Popen] = None

    def execute(self, job: TestJob) -> TestJob:
        """Execute a test job"""
        logger.info(f"Executing job {job.job_id}: {job.project_path}")

        job.status = JobStatus.RUNNING
        job.started_at = datetime.now()

        # Validate project path
        if not os.path.exists(job.project_path):
            job.status = JobStatus.FAILED
            job.error_message = f"Project path not found: {job.project_path}"
            job.completed_at = datetime.now()
            return job

        # Create artifacts directory for this job
        job_artifacts_dir = self.artifacts_dir / job.job_id
        job_artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Build command based on framework
        cmd = self._build_command(job, job_artifacts_dir)

        if not cmd:
            job.status = JobStatus.FAILED
            job.error_message = f"Unsupported framework: {job.framework}"
            job.completed_at = datetime.now()
            return job

        # Execute with timeout
        try:
            logger.info(f"Running command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=job.timeout_seconds,
                cwd=job.project_path
            )

            job.output = result.stdout + result.stderr

            # Save output to file
            log_file = job_artifacts_dir / "output.log"
            log_file.write_text(job.output)
            job.log_path = str(log_file)

            # Parse results
            self._parse_results(job, job_artifacts_dir)

            job.status = JobStatus.COMPLETE
            job.completed_at = datetime.now()

            logger.info(f"Job {job.job_id} completed: {job.result} "
                       f"({job.tests_passed}/{job.tests_run} passed)")

        except subprocess.TimeoutExpired:
            job.status = JobStatus.TIMEOUT
            job.error_message = f"Test execution exceeded {job.timeout_seconds}s timeout"
            job.completed_at = datetime.now()
            logger.warning(f"Job {job.job_id} timed out")

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            logger.error(f"Job {job.job_id} failed: {e}")

        return job

    def _build_command(self, job: TestJob, artifacts_dir: Path) -> Optional[List[str]]:
        """Build Godot command based on framework"""

        if job.framework == "gdUnit4":
            cmd = [
                "godot",
                "--path", job.project_path,
                "--headless",
                "-s", "res://addons/gdUnit4/bin/GdUnitCmdTool.gd",
                "--ignoreHeadlessMode"
            ]

            # Add test suite specification
            if job.test_suite and job.test_suite != "all":
                cmd.extend(["--test-suite", job.test_suite])
            else:
                cmd.extend(["-a", "test/"])

            # Add JUnit XML output
            junit_file = artifacts_dir / "results.xml"
            cmd.extend(["--report-format", "junit", "--report-path", str(junit_file)])
            job.junit_path = str(junit_file)

        elif job.framework == "GUT":
            cmd = [
                "godot",
                "--path", job.project_path,
                "--headless",
                "-s", "res://addons/gut/gut_cmdln.gd",
                "-gdir=res://test"
            ]

            if job.test_suite and job.test_suite != "all":
                cmd.append(f"-gtest={job.test_suite}")

        else:
            return None

        return cmd

    def _parse_results(self, job: TestJob, artifacts_dir: Path):
        """Parse test results"""

        if job.framework == "gdUnit4":
            self._parse_gdunit4(job, artifacts_dir)
        elif job.framework == "GUT":
            self._parse_gut(job)
        else:
            # Fallback: parse from output
            self._parse_generic(job)

    def _parse_gdunit4(self, job: TestJob, artifacts_dir: Path):
        """Parse gdUnit4 JUnit XML results"""
        junit_file = artifacts_dir / "results.xml"

        if not junit_file.exists():
            logger.warning(f"JUnit file not found: {junit_file}")
            self._parse_generic(job)
            return

        try:
            tree = ET.parse(junit_file)
            root = tree.getroot()

            # Extract summary
            testsuite = root.find('testsuite')
            if testsuite is not None:
                job.tests_run = int(testsuite.get('tests', 0))
                job.tests_failed = int(testsuite.get('failures', 0)) + int(testsuite.get('errors', 0))
                job.tests_passed = job.tests_run - job.tests_failed

                job.result = "passed" if job.tests_failed == 0 else "failed"

        except Exception as e:
            logger.error(f"Failed to parse JUnit XML: {e}")
            self._parse_generic(job)

    def _parse_gut(self, job: TestJob):
        """Parse GUT plain text output"""
        # GUT output format: "Tests run: X  Passing: Y  Failing: Z"
        import re

        match = re.search(r'Tests run:\s*(\d+)\s+Passing:\s*(\d+)\s+Failing:\s*(\d+)',
                         job.output)

        if match:
            job.tests_run = int(match.group(1))
            job.tests_passed = int(match.group(2))
            job.tests_failed = int(match.group(3))
            job.result = "passed" if job.tests_failed == 0 else "failed"
        else:
            self._parse_generic(job)

    def _parse_generic(self, job: TestJob):
        """Fallback parser - look for common patterns"""
        import re

        # Try to find test counts in output
        patterns = [
            r'(\d+)\s+tests.*(\d+)\s+passed.*(\d+)\s+failed',
            r'Tests:\s*(\d+),\s*Passed:\s*(\d+),\s*Failed:\s*(\d+)',
            r'PASSED.*=\s*(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, job.output, re.IGNORECASE)
            if match:
                if len(match.groups()) >= 3:
                    job.tests_run = int(match.group(1))
                    job.tests_passed = int(match.group(2))
                    job.tests_failed = int(match.group(3))
                elif len(match.groups()) == 1:
                    job.tests_passed = int(match.group(1))
                    job.tests_run = job.tests_passed
                    job.tests_failed = 0

                job.result = "passed" if job.tests_failed == 0 else "failed"
                return

        # Couldn't parse - check exit code heuristic
        if "All tests passed" in job.output or "OK" in job.output:
            job.result = "passed"
        else:
            job.result = "failed"


# Global job queue and executor
job_queue = JobQueue()
executor = None  # Initialized in main()
server_start_time = datetime.now()
total_jobs_processed = 0


def worker_thread():
    """Background worker that processes jobs from queue"""
    global total_jobs_processed

    logger.info("Worker thread started")

    while True:
        try:
            # Get next job (blocks for 1 second)
            job = job_queue.get_next(timeout=1.0)

            if job:
                # Execute the job
                job = executor.execute(job)

                # Update job in queue
                job_queue.update_job(job)

                total_jobs_processed += 1

                # TODO: Send callback if specified
                if job.callback_url:
                    try:
                        import requests
                        requests.post(job.callback_url, json=asdict(job), timeout=5)
                    except Exception as e:
                        logger.error(f"Failed to send callback: {e}")

        except Exception as e:
            logger.error(f"Worker thread error: {e}")
            time.sleep(1)


# API Endpoints

@app.route('/test/submit', methods=['POST'])
def submit_test():
    """Submit a new test job"""
    try:
        data = request.json

        # Validate required fields
        if not data.get('project_path'):
            return jsonify({'error': 'project_path is required'}), 400

        # Create job
        job = TestJob(
            job_id=str(uuid.uuid4()),
            project_path=data['project_path'],
            test_suite=data.get('test_suite', 'all'),
            framework=data.get('framework', 'gdUnit4'),
            timeout_seconds=data.get('timeout_seconds', DEFAULT_TIMEOUT),
            agent_id=data.get('agent_id'),
            task_id=data.get('task_id'),
            callback_url=data.get('callback_url'),
            priority=Priority[data.get('priority', 'NORMAL')]
        )

        # Submit to queue
        if not job_queue.submit(job):
            return jsonify({'error': 'Queue is full'}), 503

        # Return response
        position = job_queue.get_queue_position(job.job_id)
        estimated_wait = position * 120  # Rough estimate: 2 min per job

        return jsonify({
            'job_id': job.job_id,
            'status': job.status.value,
            'queue_position': position,
            'estimated_wait_seconds': estimated_wait
        }), 202

    except Exception as e:
        logger.error(f"Submit error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/test/status/<job_id>', methods=['GET'])
def get_status(job_id: str):
    """Get job status"""
    job = job_queue.get_job(job_id)

    if not job:
        return jsonify({'error': 'Job not found'}), 404

    response = {
        'job_id': job.job_id,
        'status': job.status.value,
        'submitted_at': job.submitted_at.isoformat() if job.submitted_at else None,
    }

    if job.status == JobStatus.QUEUED:
        response['queue_position'] = job_queue.get_queue_position(job_id)

    elif job.status == JobStatus.RUNNING:
        response['started_at'] = job.started_at.isoformat() if job.started_at else None
        if job.started_at:
            elapsed = (datetime.now() - job.started_at).total_seconds()
            response['elapsed_seconds'] = int(elapsed)
        response['timeout_seconds'] = job.timeout_seconds

    elif job.status in [JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.TIMEOUT]:
        response.update({
            'result': job.result,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'tests_run': job.tests_run,
            'tests_passed': job.tests_passed,
            'tests_failed': job.tests_failed,
        })

        if job.started_at and job.completed_at:
            duration = (job.completed_at - job.started_at).total_seconds()
            response['duration_seconds'] = int(duration)

        if job.log_path:
            response['artifacts'] = {
                'log': job.log_path,
                'junit': job.junit_path
            }

        if job.error_message:
            response['error_message'] = job.error_message

    return jsonify(response)


@app.route('/test/results/<job_id>', methods=['GET'])
def get_results(job_id: str):
    """Get detailed test results"""
    job = job_queue.get_job(job_id)

    if not job:
        return jsonify({'error': 'Job not found'}), 404

    if job.status not in [JobStatus.COMPLETE, JobStatus.FAILED]:
        return jsonify({'error': 'Job not complete'}), 400

    return jsonify({
        'job_id': job.job_id,
        'result': job.result,
        'summary': {
            'total': job.tests_run,
            'passed': job.tests_passed,
            'failed': job.tests_failed,
        },
        'output': job.output,
        'artifacts': {
            'log': job.log_path,
            'junit': job.junit_path
        }
    })


@app.route('/test/cancel/<job_id>', methods=['DELETE'])
def cancel_test(job_id: str):
    """Cancel a queued or running test"""
    if job_queue.cancel_job(job_id):
        return jsonify({
            'job_id': job_id,
            'status': 'cancelled',
            'cancelled_at': datetime.now().isoformat()
        })
    else:
        return jsonify({'error': 'Cannot cancel job (not found or already running)'}), 400


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    uptime = (datetime.now() - server_start_time).total_seconds()

    # Get Godot version
    godot_version = "unknown"
    try:
        result = subprocess.run(['godot', '--version'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            godot_version = result.stdout.strip()
    except:
        pass

    return jsonify({
        'status': 'healthy',
        'godot_version': godot_version,
        'uptime_seconds': int(uptime),
        'queue_depth': job_queue.get_queue_depth(),
        'active_job': job_queue.active_job.job_id if job_queue.active_job else None,
        'total_jobs_processed': total_jobs_processed,
    })


@app.route('/queue', methods=['GET'])
def view_queue():
    """View current queue"""
    active = None
    if job_queue.active_job:
        job = job_queue.active_job
        active = {
            'job_id': job.job_id,
            'agent_id': job.agent_id,
            'task_id': job.task_id,
            'started_at': job.started_at.isoformat() if job.started_at else None,
        }
        if job.started_at:
            active['elapsed_seconds'] = int((datetime.now() - job.started_at).total_seconds())

    queued_jobs = []
    with job_queue.lock:
        queued = [j for j in job_queue.jobs.values() if j.status == JobStatus.QUEUED]
        queued.sort(key=lambda j: j.submitted_at)

        for i, job in enumerate(queued, 1):
            queued_jobs.append({
                'job_id': job.job_id,
                'agent_id': job.agent_id,
                'task_id': job.task_id,
                'position': i,
                'submitted_at': job.submitted_at.isoformat() if job.submitted_at else None,
            })

    return jsonify({
        'active': active,
        'queued': queued_jobs,
        'total_queued': len(queued_jobs)
    })


def main():
    """Main entry point"""
    import argparse
    global executor

    parser = argparse.ArgumentParser(description='Godot Test Coordination Server')
    parser.add_argument('--host', default='127.0.0.1',
                       help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port to listen on (default: 5000)')
    parser.add_argument('--artifacts-dir', default=DEFAULT_ARTIFACTS_DIR,
                       help=f'Directory for test artifacts (default: {DEFAULT_ARTIFACTS_DIR})')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode')

    args = parser.parse_args()

    # Initialize executor with artifacts directory
    artifacts_path = Path(args.artifacts_dir)
    executor = TestExecutor(artifacts_path)

    # Start worker thread
    worker = threading.Thread(target=worker_thread, daemon=True)
    worker.start()

    # Start Flask server
    logger.info(f"Starting Godot Server on {args.host}:{args.port}")
    logger.info(f"Artifacts directory: {artifacts_path}")

    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)


if __name__ == '__main__':
    main()
