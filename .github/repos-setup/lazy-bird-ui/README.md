# Lazy-Bird Web UI

Modern web interface for Lazy-Bird automation engine.

## Features

- 📊 **Dashboard** - System status, active tasks, usage metrics
- 🎯 **Project Management** - Configure automation for multiple projects
- 📋 **Task Queue** - Monitor and manage task execution
- 📝 **Real-time Logs** - Stream task execution logs via SSE
- 💰 **Cost Tracking** - Monitor API usage and costs
- ⚙️ **Settings** - Manage Claude accounts, webhooks, API keys

## Tech Stack

- **React 18** + **TypeScript**
- **Vite** - Lightning-fast build tool
- **TanStack Query** - Server state management
- **Zustand** - Client state management
- **Radix UI** + **Tailwind CSS** - UI components
- **Axios** - HTTP client
- **EventSource** - SSE for real-time logs

## Quick Start

```bash
# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your API URL and key

# Start development server
npm run dev
# → http://localhost:5173

# Build for production
npm run build
```

## Environment Variables

```bash
VITE_LAZY_BIRD_API_URL=http://localhost:8000
VITE_LAZY_BIRD_API_KEY=lb_live_your_api_key_here
```

## Development

```bash
# Run dev server
npm run dev

# Run tests
npm test

# Lint code
npm run lint

# Format code
npm run format

# Type check
npm run typecheck
```

## Project Structure

```
src/
├── api/          # API client
├── components/   # React components
├── pages/        # Route pages
├── hooks/        # Custom hooks
├── stores/       # Zustand stores
├── types/        # TypeScript types
└── utils/        # Utilities
```

## Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### Netlify

```bash
# Build
npm run build

# Deploy dist/ folder
```

### Docker

```bash
# Build image
docker build -t lazy-bird-ui .

# Run container
docker run -p 3000:3000 lazy-bird-ui
```

## Contributing

See [IMPLEMENTATION.md](IMPLEMENTATION.md) for development roadmap.

## License

MIT
