# Lazy_Bird System Management Scripts

Quick reference for starting/stopping all Lazy_Bird services.

## Scripts Overview

| Script | Purpose |
|--------|---------|
| `./start.sh` | Start all services (only if not running) |
| `./stop.sh` | Stop all services |
| `./restart.sh` | Stop then start all services |
| `./status.sh` | Show status of all services |

## Services Managed

### Automation Services (systemd)
- **issue-watcher** - Monitors GitHub issues for new tasks
- **queue-processor** - Processes tasks from queue

### Web Services (manual processes)
- **Backend** - FastAPI/Flask API on port 5000 (v2.0: port 8000)
- **Frontend** - React dev server on port 5173

## Usage

### Start Everything
```bash
./start.sh
```

This will:
- Start issue-watcher (if not running)
- Start queue-processor (if not running)
- Start web backend on port 5000 (if not running)
- Start web frontend on port 5173 (if not running)

**Safe to run multiple times** - only starts what's not already running.

### Check Status
```bash
./status.sh
```

Shows:
- Which services are running (with PIDs)
- Queue status (number of tasks)
- Recent activity

### Stop Everything
```bash
./stop.sh
```

Stops all services (automation + web).

### Restart Everything
```bash
./restart.sh
```

Stops then starts all services.

## Logs

View logs for each service:

```bash
# Automation services (systemd)
journalctl --user -u issue-watcher -f
journalctl --user -u queue-processor -f

# Web services
tail -f web/backend/backend.log
tail -f web/frontend/frontend.log
```

## Individual Service Management

### Automation Services
```bash
# Start
systemctl --user start issue-watcher
systemctl --user start queue-processor

# Stop
systemctl --user stop issue-watcher queue-processor

# Status
systemctl --user status issue-watcher
systemctl --user status queue-processor
```

### Web Services
```bash
# Start manually
cd web && ./start.sh

# Stop (kill processes on ports)
lsof -ti:5000 | xargs kill
lsof -ti:5173 | xargs kill
```

## Troubleshooting

### Services won't start
1. Check logs:
   ```bash
   journalctl --user -u issue-watcher -n 50
   journalctl --user -u queue-processor -n 50
   ```

2. Check configuration:
   ```bash
   ls -la ~/.config/lazy_birtd/
   cat ~/.config/lazy_birtd/config.yml
   ```

### Web UI won't start
1. Backend venv missing:
   ```bash
   cd web/backend
   python3 -m venv venv
   ./venv/bin/pip install -r requirements.txt
   ```

2. Frontend dependencies missing:
   ```bash
   cd web/frontend
   npm install
   ```

### Duplicate processes running
```bash
# Kill old processes
./stop.sh
sleep 2
./start.sh
```

## First Time Setup

If you haven't set up the services yet:

```bash
# 1. Install systemd services
cp systemd/*.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable issue-watcher queue-processor

# 2. Set up web dependencies
cd web/backend && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cd ../frontend && npm install
cd ../..

# 3. Start everything
./start.sh
```

## Environment

All services run as user processes (no sudo required).

**Automation services** run persistently via systemd.
**Web services** run in foreground (use `nohup` in start.sh).
