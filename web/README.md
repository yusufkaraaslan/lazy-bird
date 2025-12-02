# Lazy_Bird Web UI

Modern web-based dashboard for managing Lazy_Bird automation system.

## Features

### ✅ Implemented (Phase 0)
- **Dashboard**: System overview with status cards and quick stats
- **Project Management**: Full CRUD with route-based forms (`/projects/add`, `/projects/:id/edit`)
- **Service Management**: systemd service control with dedicated form pages
- **Settings**: GitHub token configuration and service controls
- **Task Queue**: View queued tasks with detailed information
- **Modern UI**: Clean, responsive design with dark mode support
- **Route-based Navigation**: Bookmarkable URLs, browser back button support

### 🚧 Coming Soon
- **Live Logs**: Watch Claude Code execution in real-time (Phase 2)
- **GitHub Board**: Kanban-style issue management (Phase 3)
- **Real-time Updates**: WebSocket/SSE for live data (Phase 2)

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

### ⚡ One-Command Startup (Recommended)

The easiest way to start both backend and frontend together:

```bash
# From the web directory
cd web

# Start everything
./start.sh

# When done, stop everything (or just press Ctrl+C)
./stop.sh
```

**What start.sh does:**
- ✅ Checks that backend venv and frontend node_modules exist
- ✅ Starts backend server on port 5000
- ✅ Starts frontend dev server on port 5173
- ✅ Logs output to `backend.log` and `frontend.log`
- ✅ Handles cleanup on Ctrl+C

**URLs:**
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:5000`
- API Docs: `http://localhost:5000/`

**View Logs:**
```bash
# Backend logs
tail -f web/backend.log

# Frontend logs
tail -f web/frontend.log
```

### 🔧 Manual Setup (Alternative)

If you prefer to run backend and frontend separately:

#### Backend Setup

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

**Backend will be available at:** `http://localhost:5000` (or custom port)

#### Frontend Setup

```bash
# Navigate to frontend directory
cd web/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

**Frontend will be available at:** `http://localhost:5173`

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
│   │   ├── App.tsx               # Main app with routes
│   │   ├── main.tsx              # Entry point
│   │   ├── pages/                # Route pages
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── ProjectsPage.tsx  # Projects list
│   │   │   ├── ProjectFormPage.tsx  # Add/edit project (route-based)
│   │   │   ├── ServicesPage.tsx  # Services list
│   │   │   ├── ServiceFormPage.tsx  # Add/edit service (route-based)
│   │   │   ├── QueuePage.tsx
│   │   │   └── SettingsPage.tsx
│   │   ├── components/           # React components
│   │   │   ├── Layout.tsx        # Sidebar navigation
│   │   │   └── ProjectForm.tsx   # Project form component
│   │   ├── hooks/                # Custom React hooks
│   │   │   ├── useProjects.ts
│   │   │   └── useSystem.ts
│   │   ├── lib/                  # Utilities & API client
│   │   │   └── api.ts
│   │   └── types/
│   │       └── api.ts            # TypeScript types
│   ├── package.json
│   └── vite.config.ts
└── README.md                     # This file
```

## Frontend Architecture

### Route-Based Navigation

The UI uses **React Router** with dedicated pages for forms (instead of modals):

| Route | Purpose |
|-------|---------|
| `/` | Dashboard - System overview |
| `/projects` | Projects list |
| `/projects/add` | Add new project (full page form) |
| `/projects/:id/edit` | Edit existing project |
| `/services` | Services list |
| `/services/add` | Create new service (full page form) |
| `/services/:name/edit` | Edit existing service |
| `/queue` | Task queue viewer |
| `/settings` | System settings & GitHub token |

**Benefits:**
- ✅ Bookmarkable URLs
- ✅ Browser back/forward buttons work
- ✅ More space for complex forms
- ✅ Better mobile experience
- ✅ Clear navigation state

### State Management

- **TanStack Query (React Query)** - Server state management
  - Automatic caching
  - Background refetching
  - Optimistic updates
  - Mutation handling
- **React Router** - Navigation state
- **React useState** - Local UI state

### Component Structure

- **Pages** - Full page views, handle routing
- **Components** - Reusable UI components (forms, cards, etc.)
- **Hooks** - Custom hooks for API calls and business logic
- **Types** - TypeScript interfaces for type safety

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

**Recommended - One Command:**
```bash
cd web
./start.sh
```

**Alternative - Separate Terminals:**
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

### Phase 0 (✅ Complete)
- ✅ Backend API (system, projects, services, queue)
- ✅ Frontend with React + TypeScript + Vite
- ✅ Dashboard page with system status
- ✅ Projects page with CRUD operations
- ✅ Services page with systemd control
- ✅ Settings page (GitHub token, service management)
- ✅ Queue page (task viewer)
- ✅ Route-based navigation (no modals)
- ✅ Modern UI with Tailwind CSS and dark mode
- ✅ TanStack Query for data management
- ✅ Full TypeScript type safety

### Phase 1 (Next - Week 2)
- Task log viewer (view task execution logs)
- Task cancellation (cancel running tasks)
- Enhanced error handling and user feedback
- Loading states and skeleton screens
- Toast notifications

### Phase 2 (Week 3-4)
- Live Claude Code logs (Server-Sent Events)
- Real-time task status updates
- WebSocket for live data
- Task progress indicators
- Agent execution viewer

### Phase 3 (Week 5-6)
- GitHub Kanban board integration
- Issue editor with markdown preview
- Claude-assisted task planning
- Issue templates management

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
