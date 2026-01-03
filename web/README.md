# Lazy-Bird Web Backend API

**Status:** ✅ **Included in v2.0** - Production Ready
**Repository:** Part of lazy-bird core engine
**Frontend:** Moved to [lazy-bird-ui](https://github.com/yusufkaraaslan/lazy-bird-ui)

Flask-based REST API backend for Lazy-Bird automation system.

---

## 🔄 Frontend Migration Notice

**The React frontend has been moved to a separate repository:**
- **New Location**: [lazy-bird-ui](https://github.com/yusufkaraaslan/lazy-bird-ui)
- **What's Here Now**: Flask backend API only
- **Architecture**: Microservice separation (v2.0)

---

## Features

### ✅ API Endpoints
- **Projects API** - CRUD operations for automation projects
- **System API** - Service status and control
- **Queue API** - Task queue management
- **Settings API** - Configuration management
- **Issues API** - GitHub/GitLab integration
- **Agents API** - Agent status monitoring
- **Analytics API** - Usage metrics and cost tracking
- **WebSocket API** - Real-time updates and log streaming

### ✅ Real-Time Features
- **WebSocket Support** - Live updates via Socket.IO
- **Log Streaming** - Server-Sent Events (SSE)
- **Task Monitoring** - Real-time queue status

## Technology Stack

### Backend
- **Flask** 3.0.0 - Python web framework
- **Flask-CORS** - Cross-origin resource sharing
- **Flask-SocketIO** - WebSocket support
- **PyYAML** - Configuration file parsing
- **psutil** - System resource monitoring

## Quick Start

### Backend Setup

```bash
# Navigate to backend directory
cd web/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
python3 app.py

# Or with custom port
python3 app.py --port 5001 --host 127.0.0.1
```

**Backend will be available at:** `http://localhost:5000`

## API Documentation

### Projects API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | List all projects |
| GET | `/api/projects/:id` | Get specific project |
| POST | `/api/projects` | Add new project |
| PUT | `/api/projects/:id` | Update project |
| DELETE | `/api/projects/:id` | Delete project |
| POST | `/api/projects/:id/enable` | Enable project |
| POST | `/api/projects/:id/disable` | Disable project |

### System API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/system/status` | Get system status (services, resources) |
| GET | `/api/system/services/:name` | Get service status |
| POST | `/api/system/services/:name/start` | Start service |
| POST | `/api/system/services/:name/stop` | Stop service |
| POST | `/api/system/services/:name/restart` | Restart service |
| GET | `/api/system/config` | Get system configuration |
| PUT | `/api/system/config` | Update system configuration |

### Queue API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/queue` | List all queued tasks |
| GET | `/api/queue/:id` | Get specific task |
| DELETE | `/api/queue/:id` | Cancel task |
| GET | `/api/queue/stats` | Get queue statistics |

### Settings API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Get all settings |
| PUT | `/api/settings` | Update settings |
| GET | `/api/settings/github-token` | Get GitHub token status |
| POST | `/api/settings/github-token` | Update GitHub token |

### Issues API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/issues` | List GitHub/GitLab issues |
| GET | `/api/issues/:id` | Get specific issue |
| POST | `/api/issues` | Create new issue |
| PUT | `/api/issues/:id` | Update issue |

### Agents API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/agents` | List all agents |
| GET | `/api/agents/:id` | Get agent status |
| GET | `/api/agents/:id/logs` | Stream agent logs (SSE) |

### Analytics API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/costs` | Get cost breakdown |
| GET | `/api/analytics/usage` | Get usage metrics |
| GET | `/api/analytics/performance` | Get performance stats |

### WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `task.started` | Server→Client | Task execution started |
| `task.progress` | Server→Client | Task progress update |
| `task.completed` | Server→Client | Task finished |
| `log.line` | Server→Client | New log line |
| `queue.updated` | Server→Client | Queue status changed |

## Development

### Backend Development

```bash
cd web/backend
source venv/bin/activate

# Run with debug mode
python3 app.py --debug

# Run tests (when available)
pytest tests/

# Check code style
flake8 .
```

## Project Structure

```
web/
├── backend/
│   ├── app.py                    # Main Flask application
│   ├── requirements.txt          # Python dependencies
│   ├── api/
│   │   ├── projects.py           # Project CRUD endpoints
│   │   ├── system.py             # System status & control
│   │   ├── queue.py              # Task queue endpoints
│   │   ├── settings.py           # Settings management
│   │   ├── issues.py             # GitHub/GitLab issues
│   │   ├── agents.py             # Agent monitoring
│   │   ├── analytics.py          # Usage analytics
│   │   └── websocket.py          # WebSocket handlers
│   └── services/
│       ├── config_service.py     # Config.yml reader/writer
│       ├── systemd_service.py    # Service control
│       ├── queue_service.py      # Queue reader
│       ├── websocket_manager.py  # WebSocket management
│       └── log_streaming.py      # Log stream handling
└── README.md                     # This file
```

## Frontend (Moved to lazy-bird-ui)

**The React frontend is now in a separate repository:**

- **Repository**: [lazy-bird-ui](https://github.com/yusufkaraaslan/lazy-bird-ui)
- **Tech Stack**: React 18 + TypeScript + Vite
- **Features**: Dashboard, Project Management, Queue Viewer, Settings
- **Documentation**: See lazy-bird-ui repository

### Running with Frontend

```bash
# Terminal 1: Start backend (this repo)
cd web/backend
python3 app.py

# Terminal 2: Start frontend (lazy-bird-ui repo)
cd /path/to/lazy-bird-ui
npm install
npm run dev
```

**URLs:**
- Backend API: http://localhost:5000
- Frontend UI: http://localhost:5173 (lazy-bird-ui repo)

## Configuration

### Backend Configuration

The backend reads from `~/.config/lazy_birtd/config.yml` by default.

**Environment Variables:**
- `LAZY_BIRD_CONFIG_PATH` - Custom config file path
- `LAZY_BIRD_QUEUE_DIR` - Custom queue directory
- `SECRET_KEY` - Flask secret key (required for production)

## Deployment

### Development (Localhost)

```bash
cd web/backend
python3 app.py
```

### Production with Docker (Future)

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop
docker-compose down
```

### Production with gunicorn

```bash
cd web/backend
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Troubleshooting

### Backend won't start

**Error:** `ModuleNotFoundError: No module named 'flask'`
```bash
cd web/backend
pip install -r requirements.txt
```

**Error:** `Config file not found`
```bash
# Make sure Lazy_Bird is set up first
cd ../..
./wizard.sh
```

### API requests failing

**Error:** `CORS policy: No 'Access-Control-Allow-Origin' header`
- Make sure backend is running
- Verify CORS is enabled in `backend/app.py`
- Check frontend is using correct API URL

**Error:** `404 Not Found` on API endpoints
- Verify backend is running on correct port
- Test API directly: `curl http://localhost:5000/api/projects`

### WebSocket connection issues

**Error:** `WebSocket connection failed`
- Check that Socket.IO is properly initialized
- Verify CORS origins include frontend URL
- Test with: `curl http://localhost:5000/socket.io/?EIO=4&transport=polling`

## API Versioning

**Current Version:** v1

All endpoints are prefixed with `/api/` and currently use implicit v1.
Future versions will use `/api/v2/` etc.

## Rate Limiting

Currently no rate limiting. To be added in future versions.

## Authentication

Currently using basic API key authentication. OAuth2 support planned for future versions.

## Contributing

1. Create feature branch: `git checkout -b feature/api-endpoint`
2. Make changes to backend only
3. Test endpoints: `pytest tests/`
4. Create pull request

## Frontend Development

**Frontend development has moved to [lazy-bird-ui](https://github.com/yusufkaraaslan/lazy-bird-ui)**

For frontend changes:
1. Clone lazy-bird-ui repository
2. Follow lazy-bird-ui CONTRIBUTING guide
3. Submit PRs to lazy-bird-ui repository

## License

MIT License - Part of Lazy-Bird project

## Support

- **API Documentation:** See [API_GUIDE.md](../Docs/API_GUIDE.md)
- **Backend Issues:** [GitHub Issues](https://github.com/yusufkaraaslan/lazy-bird/issues)
- **Frontend Issues:** [lazy-bird-ui Issues](https://github.com/yusufkaraaslan/lazy-bird-ui/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yusufkaraaslan/lazy-bird/discussions)
