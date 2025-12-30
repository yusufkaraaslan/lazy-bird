# Lazy-Bird v2.0 - Multi-Repository Setup Guide

## Overview

The v2.0 refactor splits Lazy-Bird into 3 separate repositories for clean microservice architecture.

## Repository Structure

```
lazy-bird/                           # Core Engine (This Repo)
├── FastAPI REST API
├── PostgreSQL Database
├── Celery Task Queue
├── Webhook Publisher
└── Git/Claude Services

lazy-bird-ui/                        # Web UI Client (New Repo)
├── React + TypeScript
├── Vite Build System
├── API Client Library
├── Dashboard Components
└── Real-time Log Viewer

plane-lazy-bird-integration/        # Plane Client (New Repo)
├── Django Package
├── API Client Wrapper
├── Signal Handlers
├── Webhook Receiver
└── Admin Integration
```

## Repository Setup Instructions

### 1. Create GitHub Repositories

```bash
# Create lazy-bird-ui repository
gh repo create yusufkaraaslan/lazy-bird-ui \
  --public \
  --description "Web UI for Lazy-Bird automation engine" \
  --clone

# Create plane-lazy-bird-integration repository
gh repo create yusufkaraaslan/plane-lazy-bird-integration \
  --public \
  --description "Plane integration for Lazy-Bird automation" \
  --clone
```

### 2. Initialize Repository Structure

#### For lazy-bird-ui:

```bash
cd lazy-bird-ui

# Copy initialization files from template
cp ../lazy-bird/.github/repos-setup/lazy-bird-ui/* .

# Initialize npm project
npm create vite@latest . -- --template react-ts

# Install dependencies
npm install @tanstack/react-query axios zustand @radix-ui/react-* class-variance-authority clsx tailwind-merge

# Create directory structure
mkdir -p src/{api,components,pages,hooks,stores,types,utils}

# Initial commit
git add .
git commit -m "Initial commit: Project setup"
git push -u origin main
```

#### For plane-lazy-bird-integration:

```bash
cd plane-lazy-bird-integration

# Copy initialization files from template
cp ../lazy-bird/.github/repos-setup/plane-lazy-bird-integration/* .

# Initialize Python package
poetry init --name plane-lazy-bird --dependency httpx --dependency django

# Create directory structure
mkdir -p plane_lazy_bird/{templates,static,management/commands}

# Initial commit
git add .
git commit -m "Initial commit: Django package setup"
git push -u origin main
```

### 3. Set Up GitHub Projects

Each repository gets its own GitHub Project board:

#### lazy-bird Project Board
```bash
gh project create \
  --owner yusufkaraaslan \
  --title "Lazy-Bird v2.0 Core Engine" \
  --body "Core engine refactoring to microservice architecture"
```

**Columns**:
- 📋 Backlog
- 🎯 Ready
- 🚧 In Progress
- 👀 In Review
- ✅ Done

#### lazy-bird-ui Project Board
```bash
gh project create \
  --owner yusufkaraaslan \
  --title "Lazy-Bird UI Development" \
  --body "Web UI client for Lazy-Bird"
```

**Columns**: Same as above

#### plane-lazy-bird-integration Project Board
```bash
gh project create \
  --owner yusufkaraaslan \
  --title "Plane Integration Development" \
  --body "Plane integration client for Lazy-Bird"
```

**Columns**: Same as above

### 4. Create Milestones

#### lazy-bird milestones:
- **v2.0-week1**: Foundation & Database (Week 1)
- **v2.0-week2**: API Endpoints & Services (Week 2)
- **v2.0-week3**: Background Tasks & Webhooks (Week 3)
- **v2.0-alpha**: Alpha Release (End of Week 3)
- **v2.0-beta**: Beta Release (End of Week 5)
- **v2.0.0**: Production Release (End of Week 6)

#### lazy-bird-ui milestones:
- **v0.1.0**: Initial Setup & API Client (Week 4, Day 1-2)
- **v0.2.0**: Core Components (Week 4, Day 3-4)
- **v0.3.0**: Dashboard & Features (Week 4, Day 5)
- **v1.0.0**: Production Ready (Week 6)

#### plane-lazy-bird-integration milestones:
- **v0.1.0**: Package Setup & API Client (Week 4, Day 1)
- **v0.2.0**: Signals & Webhooks (Week 4, Day 2)
- **v1.0.0**: Production Ready (Week 6)

### 5. Create Issues from Templates

```bash
# In each repository, run:
# This will create all issues from the ISSUES.md file

cd lazy-bird
python .github/scripts/create_issues.py

cd ../lazy-bird-ui
python .github/scripts/create_issues.py

cd ../plane-lazy-bird-integration
python .github/scripts/create_issues.py
```

## Dependencies Between Repositories

```
lazy-bird (Core)
    ↓
    ├─→ lazy-bird-ui (depends on API being ready)
    └─→ plane-lazy-bird-integration (depends on API being ready)
```

**Critical Path**:
1. lazy-bird Week 1-3 (Database, API, Services)
2. lazy-bird Week 3 end: API endpoints functional ← **Blocking point**
3. lazy-bird-ui + plane-lazy-bird-integration Week 4 (parallel development)

## Development Workflow

### Phase 1: Core Engine (Week 1-3)
**Repository**: lazy-bird
**Branch**: `refactor/v2.0`

Focus 100% on core engine. Other repos wait.

### Phase 2: Client Development (Week 4)
**Repositories**: All three in parallel

Once core API is functional:
- lazy-bird: Polish, testing, documentation
- lazy-bird-ui: Full development
- plane-lazy-bird-integration: Full development

### Phase 3: Integration Testing (Week 5)
**Repositories**: All three

End-to-end testing across all repos.

### Phase 4: Production Release (Week 6)
**Repositories**: All three

Deploy and monitor.

## Communication Between Repos

### Issue Cross-References

Use GitHub issue references across repos:

```markdown
# In lazy-bird-ui issue
Blocked by: yusufkaraaslan/lazy-bird#42 (API endpoint not ready)

# In lazy-bird issue
Unblocks: yusufkaraaslan/lazy-bird-ui#12 (Dashboard needs this API)
```

### Status Updates

Use labels across all repos:
- `status:blocked` - Blocked by another issue/repo
- `status:blocking` - Blocking other issues/repos
- `cross-repo` - Affects multiple repositories
- `api-breaking` - Breaking API change (requires coordination)

## Next Steps

1. ✅ Read this setup guide
2. ⬜ Create the two new GitHub repositories
3. ⬜ Copy initialization files to new repos
4. ⬜ Set up GitHub Projects for each repo
5. ⬜ Create milestones in each repo
6. ⬜ Generate issues from templates
7. ⬜ Review and prioritize issues
8. ⬜ Start Week 1 development in lazy-bird

---

**Ready to proceed?** See repository-specific setup guides:
- [lazy-bird-ui Setup](lazy-bird-ui/SETUP.md)
- [plane-lazy-bird-integration Setup](plane-lazy-bird-integration/SETUP.md)
