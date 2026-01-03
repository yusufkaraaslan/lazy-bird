# Godot Server - Coordination Service Specification

**Applies to:** lazy-bird core engine (Phase 2 - Multi-Agent)
**Related repos:** lazy-bird (core) - NOT lazy-bird-ui or plane-lazy-bird-integration
**Status:** 📋 **Planned for Future** - Phase 2 multi-agent implementation
**v2.0 Note:** Current v2.0 uses Celery task queue; Godot Server planned for Phase 2+

## Problem Statement

When multiple Claude Code agents work on different tasks simultaneously, they may need to run Godot tests. However, Godot cannot safely handle concurrent test execution on the same project - this leads to:

- File locks and corruption
- Test result conflicts
- Resource contention (GPU, project files)
- Unreliable test outcomes

**Solution:** A centralized Godot Server that queues and executes test requests sequentially, allowing multiple agents to coordinate safely.

## Architecture Overview

```
┌─────────────────────┐
│  Claude Agent 1     │────┐
│  (Task #42)         │    │
└─────────────────────┘    │
                           │
┌─────────────────────┐    │    ┌──────────────────────┐
│  Claude Agent 2     │────┼───→│   Godot Server       │
│  (Task #43)         │    │    │   (HTTP API)         │
└─────────────────────┘    │    └──────────┬───────────┘
                           │               │
┌─────────────────────┐    │               │
│  Claude Agent 3     │────┘               ↓
│  (Task #44)         │           ┌──────────────────┐
└─────────────────────┘           │  Godot Process   │
                                  │  (Headless Mode) │
                                  └──────────────────┘

Request Queue:          Test Execution:
1. Agent 2 → Job #123   Running: Job #123 (Agent 2)
2. Agent 1 → Job #124   Pending: Job #124, #125
3. Agent 3 → Job #125
```

## Core Components

### 1. HTTP API Server

**Technology:** Python Flask (lightweight, easy to deploy)

**Endpoints:**

#### POST /test/submit
Submit a new test request

**Request:**
```json
{
  "project_path": "/tmp/agents/agent-42/my-game",
  "test_suite": "all",  // or "res://test/specific_test.gd"
  "framework": "gdUnit4",  // or "GUT"
  "timeout_seconds": 300,
  "agent_id": "agent-42",
  "task_id": 42,
  "callback_url": "http://localhost:8001/test-complete"  // optional
}
```

**Response:**
```json
{
  "job_id": "job-123",
  "status": "queued",
  "queue_position": 2,
  "estimated_wait_seconds": 120
}
```

#### GET /test/status/{job_id}
Check test status

**Response (Queued):**
```json
{
  "job_id": "job-123",
  "status": "queued",
  "queue_position": 1,
  "submitted_at": "2025-11-01T10:30:00Z",
  "estimated_start": "2025-11-01T10:32:00Z"
}
```

**Response (Running):**
```json
{
  "job_id": "job-123",
  "status": "running",
  "started_at": "2025-11-01T10:32:15Z",
  "elapsed_seconds": 45,
  "timeout_seconds": 300
}
```

**Response (Complete):**
```json
{
  "job_id": "job-123",
  "status": "complete",
  "result": "passed",  // or "failed"
  "started_at": "2025-11-01T10:32:15Z",
  "completed_at": "2025-11-01T10:34:30Z",
  "duration_seconds": 135,
  "tests_run": 15,
  "tests_passed": 15,
  "tests_failed": 0,
  "output": "...",  // full test output
  "artifacts": {
    "log": "/var/lib/lazy_birtd/tests/job-123/output.log",
    "junit": "/var/lib/lazy_birtd/tests/job-123/results.xml"
  }
}
```

#### GET /test/results/{job_id}
Get detailed test results

**Response:**
```json
{
  "job_id": "job-123",
  "result": "passed",
  "summary": {
    "total": 15,
    "passed": 15,
    "failed": 0,
    "skipped": 0,
    "errors": 0
  },
  "tests": [
    {
      "name": "test_player_health",
      "status": "passed",
      "duration_ms": 245,
      "output": "..."
    },
    // ... more tests
  ],
  "coverage": {
    "lines_covered": 450,
    "lines_total": 520,
    "percentage": 86.5
  },
  "artifacts": {
    "full_log": "http://localhost:5000/artifacts/job-123/output.log",
    "junit_xml": "http://localhost:5000/artifacts/job-123/results.xml",
    "html_report": "http://localhost:5000/artifacts/job-123/report.html"
  }
}
```

#### DELETE /test/cancel/{job_id}
Cancel a queued or running test

**Response:**
```json
{
  "job_id": "job-123",
  "status": "cancelled",
  "was_running": true,
  "cancelled_at": "2025-11-01T10:33:00Z"
}
```

#### GET /health
Health check

**Response:**
```json
{
  "status": "healthy",
  "godot_version": "4.2.1",
  "uptime_seconds": 86400,
  "queue_depth": 2,
  "active_job": "job-123",
  "total_jobs_processed": 1543,
  "average_test_time_seconds": 127,
  "last_test_completed": "2025-11-01T10:30:00Z"
}
```

#### GET /queue
View current queue

**Response:**
```json
{
  "active": {
    "job_id": "job-123",
    "agent_id": "agent-42",
    "task_id": 42,
    "started_at": "2025-11-01T10:32:15Z",
    "elapsed_seconds": 45
  },
  "queued": [
    {
      "job_id": "job-124",
      "agent_id": "agent-41",
      "task_id": 41,
      "position": 1,
      "submitted_at": "2025-11-01T10:32:30Z"
    },
    {
      "job_id": "job-125",
      "agent_id": "agent-43",
      "task_id": 43,
      "position": 2,
      "submitted_at": "2025-11-01T10:33:00Z"
    }
  ],
  "total_queued": 2
}
```

### 2. Job Queue Manager

**Queue Implementation:** Python `queue.Queue` (thread-safe) or Redis for persistence

**Job Lifecycle:**
```
submitted → queued → running → [complete|failed|timeout|cancelled]
```

**Queue Properties:**
- FIFO (First In, First Out)
- Optional priority levels (high/normal/low)
- Maximum queue size (default: 50)
- Job timeout enforcement
- Automatic cleanup of old jobs (> 7 days)

**Priority Handling:**
```python
class Priority(Enum):
    HIGH = 1    # Retry attempts, critical fixes
    NORMAL = 2  # Regular tasks
    LOW = 3     # Non-blocking refactors
```

### 3. Test Executor

**Responsibilities:**
- Launch Godot in headless mode
- Execute tests from job specification
- Capture output (stdout, stderr)
- Parse test results
- Handle timeouts
- Clean up resources

**Execution Flow:**
```python
def execute_test(job):
    # 1. Validate project path exists
    if not os.path.exists(job.project_path):
        return error("Project path not found")

    # 2. Determine test command based on framework
    if job.framework == "gdUnit4":
        cmd = [
            "godot",
            "--path", job.project_path,
            "--headless",
            "-s", "res://addons/gdUnit4/bin/GdUnitCmdTool.gd",
            "--test-suite", job.test_suite,
            "--report-format", "junit"
        ]
    elif job.framework == "GUT":
        cmd = [
            "godot",
            "--path", job.project_path,
            "--headless",
            "-s", "res://addons/gut/gut_cmdln.gd",
            "-gdir=res://test"
        ]

    # 3. Execute with timeout
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=job.timeout_seconds,
            cwd=job.project_path
        )
    except subprocess.TimeoutExpired:
        return timeout_result(job)

    # 4. Parse results
    results = parse_test_output(result.stdout, job.framework)

    # 5. Save artifacts
    save_artifacts(job.job_id, result.stdout, results)

    # 6. Callback if specified
    if job.callback_url:
        notify_callback(job.callback_url, results)

    return results
```

### 4. Result Parser

**Supported Formats:**
- gdUnit4 JUnit XML output
- GUT plain text output
- TAP (Test Anything Protocol)
- Custom regex patterns

**Parser Interface:**
```python
class TestResultParser:
    def parse(self, output: str, framework: str) -> TestResult:
        """Parse test output into structured result"""
        pass

    def extract_summary(self, output: str) -> TestSummary:
        """Extract pass/fail counts"""
        pass

    def extract_individual_tests(self, output: str) -> List[Test]:
        """Parse individual test results"""
        pass
```

**gdUnit4 Parsing:**
```python
def parse_gdunit4(xml_file: str) -> TestResult:
    tree = ET.parse(xml_file)
    root = tree.getroot()

    tests = []
    for testcase in root.findall('.//testcase'):
        test = {
            'name': testcase.get('name'),
            'classname': testcase.get('classname'),
            'time': float(testcase.get('time')),
            'status': 'passed'
        }

        failure = testcase.find('failure')
        if failure is not None:
            test['status'] = 'failed'
            test['message'] = failure.get('message')
            test['output'] = failure.text

        tests.append(test)

    return TestResult(tests=tests)
```

### 5. Resource Monitor

**Monitors:**
- CPU usage by Godot process
- Memory consumption
- Disk I/O
- Test duration

**Actions:**
- Kill hung processes after timeout
- Alert if resource usage excessive
- Restart Godot if it becomes unresponsive
- Log resource metrics for analysis

**Implementation:**
```python
import psutil

class ResourceMonitor:
    def __init__(self, process: subprocess.Popen):
        self.process = psutil.Process(process.pid)

    def check_health(self) -> dict:
        return {
            'cpu_percent': self.process.cpu_percent(),
            'memory_mb': self.process.memory_info().rss / 1024 / 1024,
            'status': self.process.status(),
            'num_threads': self.process.num_threads()
        }

    def is_hung(self) -> bool:
        # No CPU activity for 60 seconds = hung
        cpu = self.process.cpu_percent(interval=60)
        return cpu < 0.1 and self.process.status() != 'sleeping'
```

## Deployment Options

### Option 1: systemd Service (Recommended for Linux)

**Service File:** `/etc/systemd/system/godot-server.service`
```ini
[Unit]
Description=Lazy_Birtd Godot Test Server
After=network.target

[Service]
Type=simple
User=lazybirtd
WorkingDirectory=/opt/lazy_birtd
ExecStart=/usr/bin/python3 /opt/lazy_birtd/scripts/godot-server.py
Restart=always
RestartSec=10

# Resource limits
MemoryLimit=4G
CPUQuota=200%

# Logging
StandardOutput=journal
StandardError=journal

# Environment
Environment="GODOT_BIN=/usr/bin/godot"
Environment="TEST_ARTIFACTS_DIR=/var/lib/lazy_birtd/tests"
Environment="MAX_QUEUE_SIZE=50"

[Install]
WantedBy=multi-user.target
```

**Management:**
```bash
sudo systemctl start godot-server
sudo systemctl enable godot-server
sudo systemctl status godot-server
journalctl -u godot-server -f
```

### Option 2: Docker Container

**Dockerfile:**
```dockerfile
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Godot
RUN wget https://downloads.tuxfamily.org/godotengine/4.2.1/Godot_v4.2.1-stable_linux.x86_64.zip \
    && unzip Godot_v4.2.1-stable_linux.x86_64.zip \
    && mv Godot_v4.2.1-stable_linux.x86_64 /usr/local/bin/godot \
    && chmod +x /usr/local/bin/godot \
    && rm Godot_v4.2.1-stable_linux.x86_64.zip

# Install Python dependencies
COPY requirements.txt /app/
RUN pip3 install -r /app/requirements.txt

# Copy application
COPY scripts/godot-server.py /app/
COPY scripts/test_parsers.py /app/

# Create artifacts directory
RUN mkdir -p /var/lib/lazy_birtd/tests

WORKDIR /app

# Expose API port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Run server
CMD ["python3", "godot-server.py"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  godot-server:
    build: .
    container_name: lazy_birtd_godot_server
    ports:
      - "5000:5000"
    volumes:
      - ./test-artifacts:/var/lib/lazy_birtd/tests
      - /tmp/agents:/tmp/agents:ro  # Mount agent worktrees (read-only)
    environment:
      - MAX_QUEUE_SIZE=50
      - DEFAULT_TIMEOUT=300
      - CLEANUP_DAYS=7
    restart: unless-stopped
    mem_limit: 4g
    cpus: 2
```

## Configuration

**Config File:** `/etc/lazy_birtd/godot-server.conf`
```yaml
server:
  host: 0.0.0.0
  port: 5000
  workers: 1  # Single worker for sequential execution

godot:
  binary: /usr/bin/godot
  timeout_default: 300  # 5 minutes
  timeout_max: 1800     # 30 minutes

queue:
  max_size: 50
  enable_priority: true

storage:
  artifacts_dir: /var/lib/lazy_birtd/tests
  cleanup_days: 7
  max_size_gb: 20

logging:
  level: INFO
  file: /var/log/lazy_birtd/godot-server.log
  max_size_mb: 100
  backup_count: 5

monitoring:
  enable_metrics: true
  metrics_port: 9090  # Prometheus format
```

## Client Library

**Python Client for Agents:**
```python
# godot_client.py
import requests
import time

class GodotClient:
    def __init__(self, server_url="http://localhost:5000"):
        self.server_url = server_url

    def submit_test(self, project_path, test_suite="all",
                    framework="gdUnit4", timeout=300):
        """Submit a test job and return job_id"""
        response = requests.post(
            f"{self.server_url}/test/submit",
            json={
                "project_path": project_path,
                "test_suite": test_suite,
                "framework": framework,
                "timeout_seconds": timeout
            }
        )
        response.raise_for_status()
        return response.json()["job_id"]

    def wait_for_result(self, job_id, poll_interval=5):
        """Poll until test completes, return result"""
        while True:
            status = self.get_status(job_id)

            if status["status"] == "complete":
                return self.get_results(job_id)
            elif status["status"] in ["failed", "timeout", "cancelled"]:
                raise TestFailedException(status)

            time.sleep(poll_interval)

    def get_status(self, job_id):
        """Get current status of a job"""
        response = requests.get(f"{self.server_url}/test/status/{job_id}")
        response.raise_for_status()
        return response.json()

    def get_results(self, job_id):
        """Get detailed test results"""
        response = requests.get(f"{self.server_url}/test/results/{job_id}")
        response.raise_for_status()
        return response.json()

    def cancel(self, job_id):
        """Cancel a job"""
        response = requests.delete(f"{self.server_url}/test/cancel/{job_id}")
        response.raise_for_status()
        return response.json()

# Usage in agent script:
client = GodotClient()
job_id = client.submit_test("/tmp/agents/agent-42/my-game")
print(f"Test submitted: {job_id}")

result = client.wait_for_result(job_id)
if result["result"] == "passed":
    print("✅ All tests passed!")
else:
    print(f"❌ Tests failed: {result['summary']['failed']} failures")
```

## Error Handling

### Godot Crashes
```python
# If Godot process dies unexpectedly
def handle_godot_crash(job):
    # 1. Mark job as failed
    job.status = "failed"
    job.error = "Godot process crashed"

    # 2. Save crash log if available
    save_crash_log(job.job_id)

    # 3. Restart Godot for next job
    restart_godot()

    # 4. Notify agent
    notify_agent(job.agent_id, "Test failed due to Godot crash")
```

### Timeouts
```python
# If test exceeds timeout
def handle_timeout(job):
    # 1. Kill Godot process
    kill_godot_process()

    # 2. Mark job as timeout
    job.status = "timeout"
    job.error = f"Test exceeded {job.timeout_seconds}s timeout"

    # 3. Capture partial output
    save_partial_output(job.job_id)

    # 4. Restart Godot
    restart_godot()
```

### Invalid Project Path
```python
# If project doesn't exist
def handle_invalid_project(job):
    job.status = "failed"
    job.error = f"Project path not found: {job.project_path}"
    # Don't tie up queue, fail immediately
```

## Performance Considerations

### Optimization Strategies

1. **Godot Process Reuse**
   - Keep Godot running between tests (if possible)
   - Faster than starting fresh each time
   - Risk: state leakage between tests

2. **Test Subset Execution**
   - Allow running specific test files, not always full suite
   - Faster feedback for targeted changes

3. **Parallel Godot Instances** (Future)
   - Run multiple Godot processes for different projects
   - Requires resource isolation
   - More complex scheduling

4. **Test Caching** (Future)
   - Cache results for unchanged code
   - Hash-based invalidation
   - Significant speedup for large suites

### Resource Limits

**Recommended:**
- RAM: 2-4GB per Godot instance
- CPU: 1-2 cores per instance
- Disk: 100MB per test run (artifacts)

**Monitoring:**
- Alert if queue depth > 10 (bottleneck)
- Alert if average test time > 5 minutes (slow tests)
- Alert if Godot uses > 4GB RAM (memory leak)

## Testing the Server

### Unit Tests
```bash
# Test API endpoints
pytest tests/godot_server/test_api.py

# Test queue manager
pytest tests/godot_server/test_queue.py

# Test parsers
pytest tests/godot_server/test_parsers.py
```

### Integration Tests
```bash
# End-to-end with real Godot
pytest tests/godot_server/test_integration.py

# Load testing
pytest tests/godot_server/test_load.py
```

### Manual Testing
```bash
# Start server
python3 scripts/godot-server.py

# Submit test via curl
curl -X POST http://localhost:5000/test/submit \
  -H "Content-Type: application/json" \
  -d '{"project_path": "/path/to/project", "test_suite": "all", "framework": "gdUnit4"}'

# Check status
curl http://localhost:5000/test/status/job-1

# View queue
curl http://localhost:5000/queue
```

## Monitoring & Observability

### Metrics (Prometheus Format)
```
# Exposed on :9090/metrics
godot_server_queue_depth 2
godot_server_jobs_total 1543
godot_server_jobs_passed 1421
godot_server_jobs_failed 122
godot_server_average_duration_seconds 127
godot_server_godot_restarts_total 3
godot_server_uptime_seconds 86400
```

### Logs
```
2025-11-01 10:32:15 INFO - Job job-123 submitted by agent-42
2025-11-01 10:32:15 INFO - Job job-123 started execution
2025-11-01 10:34:30 INFO - Job job-123 completed: passed (15/15 tests)
2025-11-01 10:34:31 INFO - Job job-124 started execution
```

### Dashboard (Future)
- Real-time queue visualization
- Test success rate over time
- Average test duration trends
- Resource usage graphs

## Future Enhancements

### Planned Features
1. **Smart Test Selection** - Only run tests affected by changes
2. **Parallel Execution** - Multiple Godot instances for different projects
3. **Test Sharding** - Split large test suites across instances
4. **Result Caching** - Skip unchanged tests
5. **Visual Test Recording** - Capture screenshots/videos of test runs
6. **Performance Benchmarking** - Track test performance over time

## Conclusion

The Godot Server is a critical component that enables safe concurrent development by multiple Claude agents. By centralizing test execution and providing a simple HTTP API, it eliminates the complexity and risks of direct Godot access while providing reliable, fast test feedback.

**Key Benefits:**
- ✅ Safe concurrent access to Godot
- ✅ Simple HTTP API for agents
- ✅ Reliable test execution
- ✅ Resource management
- ✅ Easy to monitor and debug
- ✅ Scalable architecture

This design ensures that automated game development can scale from a single agent to many, without sacrificing reliability or test quality.
