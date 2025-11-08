# Lazy_Bird Web UI

Modern web-based dashboard for managing Lazy_Bird automation system.

## Features

- **Project Management**: Add, edit, remove, and configure multiple projects
- **System Status**: Monitor services, resource usage, and system health
- **Task Queue**: View queued tasks, their status, and cancel if needed
- **Live Logs**: Watch Claude Code execution in real-time (Phase 2)
- **GitHub Board**: Kanban-style issue management (Phase 3)

## Technology Stack

### Backend
- **Flask** 3.0.0 - Python web framework
- **Flask-CORS** - Cross-origin resource sharing
- **PyYAML** - Configuration file parsing
- **psutil** - System resource monitoring

### Frontend
- **React** 18+ with TypeScript
- **Vite** - Build tool and dev server
- **Shadcn/ui** - UI component library
- **TanStack Query** - Server state management
- **React Router** - Client-side routing
- **Tailwind CSS** - Utility-first styling

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

**Backend will be available at:** `http://localhost:5001`

### Frontend Setup

```bash
# Navigate to frontend directory
cd web/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

**Frontend will be available at:** `http://localhost:3000` or `http://localhost:5173`

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

### Frontend Development

```bash
cd web/frontend

# Start dev server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

## Project Structure

```
web/
├── backend/
│   ├── app.py                    # Main Flask application
│   ├── requirements.txt
│   ├── api/
│   │   ├── projects.py           # Project CRUD endpoints
│   │   ├── system.py             # System status & control
│   │   └── queue.py              # Task queue endpoints
│   └── services/
│       ├── config_service.py     # Config.yml reader/writer
│       ├── systemd_service.py    # Service control
│       └── queue_service.py      # Queue reader
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/                # Route pages
│   │   ├── components/           # React components
│   │   ├── hooks/                # Custom React hooks
│   │   └── lib/                  # Utilities & API client
│   ├── package.json
│   └── vite.config.ts
└── README.md                     # This file
```

## Configuration

### Backend Configuration

The backend reads from `~/.config/lazy_birtd/config.yml` by default.

**Environment Variables:**
- `LAZY_BIRD_CONFIG_PATH` - Custom config file path
- `LAZY_BIRD_QUEUE_DIR` - Custom queue directory

### Frontend Configuration

Edit `frontend/src/lib/api.ts` to change API base URL:

```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';
```

## Deployment

### Development (Localhost Only)

```bash
# Terminal 1: Backend
cd web/backend && python3 app.py

# Terminal 2: Frontend
cd web/frontend && npm run dev
```

### Production with Docker (Future)

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
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

### Frontend won't start

**Error:** `command not found: npm`
```bash
# Install Node.js
# Ubuntu/Debian:
sudo apt install nodejs npm

# Manjaro/Arch:
sudo pacman -S nodejs npm
```

**Error:** `EADDRINUSE: address already in use`
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

### API requests failing

**Error:** `CORS policy: No 'Access-Control-Allow-Origin' header`
- Make sure backend is running
- Check frontend is using correct API URL
- Verify CORS is enabled in `backend/app.py`

**Error:** `404 Not Found` on API endpoints
- Verify backend is running on correct port
- Check API base URL in frontend config
- Test API directly: `curl http://localhost:5001/api/projects`

## Phase Roadmap

### Phase 0 (Current - Week 1)
- ✅ Backend API (system, projects, queue)
- ✅ Frontend skeleton
- ⏳ Dashboard page
- ⏳ Projects page

### Phase 1 (Week 2)
- Full project CRUD UI
- Service control buttons
- Log viewer

### Phase 2 (Week 3-4)
- Live Claude Code logs (SSE)
- Task queue with real-time updates
- Cancel running tasks

### Phase 3 (Week 5-6)
- GitHub Kanban board
- Issue editor with markdown
- Claude-assisted planning

## Contributing

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes
3. Test thoroughly
4. Create pull request

## License

MIT License - Part of Lazy_Bird project

## Support

- **Documentation:** See main [CLAUDE.md](../CLAUDE.md)
- **Issues:** [GitHub Issues](https://github.com/yusyus/lazy-bird/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yusyus/lazy-bird/discussions)
