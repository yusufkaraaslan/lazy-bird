# Repository Analysis & Reorganization Plan

**Date:** 2026-01-03
**Current Repo:** lazy-bird (core)
**Related Repos:** lazy-bird-ui, plane-lazy-bird-integration

---

## 🔍 Current Problems

### Problem 1: Too Many Root Markdown Files (15 files!)

**Current Root MD Files:**
```
├── CHANGELOG.md              ✅ Keep (standard)
├── CLAUDE.md                 ✅ Keep (project instructions)
├── CODE_OF_CONDUCT.md        ✅ Keep (standard)
├── CONTRIBUTING.md           ✅ Keep (standard)
├── README.md                 ✅ Keep (main entry point)
├── DOCKER.md                 ❌ Move to Docs/Deployment/
├── DOCS_AUDIT.md             ❌ Move to Docs/
├── E2E_TEST_SUCCESS_SUMMARY.md ❌ Move to Docs/Testing/
├── INSTALL.md                ❌ Move to Docs/Installation/
├── MANAGEMENT_SCRIPTS.md     ❌ Move to Docs/Operations/
├── PHASE0_UI_SUMMARY.md      ❌ Move to Docs/Archive/v2-migration/
├── REFACTOR_PLAN.md          ❌ Move to Docs/Planning/
├── SETUP_PROJECT.md          ❌ Move to Docs/Installation/
├── TEST_RESULTS_SUMMARY.md   ❌ Move to Docs/Testing/
└── WORKFLOW_FIXES_REPORT.md  ❌ Move to Docs/Archive/v2-migration/
```

**Only 5 files should be in root:**
1. README.md
2. CLAUDE.md
3. CHANGELOG.md
4. CONTRIBUTING.md
5. CODE_OF_CONDUCT.md
6. LICENSE (already correct)

### Problem 2: Wrong Repository - Web UI Should Not Be Here

**Current Situation:**
- `web/` directory (backend + frontend) is in lazy-bird core repo
- This violates the multi-repository architecture

**According to Architecture:**
```
lazy-bird/              → Core engine (FastAPI + PostgreSQL)
lazy-bird-ui/           → Web UI (React standalone)
plane-lazy-bird-integration/ → Plane client (Django package)
```

**The `web/` directory should be moved to lazy-bird-ui repository.**

### Problem 3: Setup Files for Other Repos

**Current Location:**
```
.github/repos-setup/
├── lazy-bird-ui/               ❌ Should be in lazy-bird-ui repo
│   ├── IMPLEMENTATION.md
│   └── README.md
└── plane-lazy-bird-integration/ ❌ Should be in plane-integration repo
    ├── IMPLEMENTATION.md
    └── README.md
```

These setup files should be in their respective repositories, not here.

### Problem 4: Symlink Loop Issue

**Problematic Symlink:**
```
lazy_bird/web/ → ../web
```

This creates a circular reference and should be removed when web/ is moved.

---

## ✅ Proposed Folder Structure

### Root Directory (Minimal)

```
/lazy-bird/
├── LICENSE                          ✅ Keep
├── README.md                        ✅ Keep (main entry point)
├── CLAUDE.md                        ✅ Keep (project instructions)
├── CHANGELOG.md                     ✅ Keep (version history)
├── CONTRIBUTING.md                  ✅ Keep (contributor guide)
├── CODE_OF_CONDUCT.md               ✅ Keep (community standards)
│
├── Docs/                            📁 Reorganized documentation
├── lazy_bird/                       📁 Core Python package
├── scripts/                         📁 Automation scripts
├── tests/                           📁 Test suite
├── docker/                          📁 Docker configs
├── systemd/                         📁 systemd services
├── nginx/                           📁 nginx configs
├── alembic/                         📁 Database migrations
├── config/                          📁 Configuration templates
└── assets/                          📁 Static assets
```

### Docs/ Directory (Organized)

```
Docs/
├── README.md                        📋 Documentation hub (NEW)
│
├── Installation/                    📁 Setup guides
│   ├── INSTALL.md                   ← From root
│   ├── SETUP_PROJECT.md             ← From root
│   └── quick-start.md               (if needed)
│
├── Operations/                      📁 Running the system
│   ├── MANAGEMENT_SCRIPTS.md        ← From root
│   ├── DOCKER.md                    ← From root (or merge with Deployment)
│   └── monitoring.md                (future)
│
├── Testing/                         📁 Test documentation
│   ├── TEST_RESULTS_SUMMARY.md      ← From root
│   ├── E2E_TEST_SUCCESS_SUMMARY.md  ← From root
│   └── testing-guide.md             (if needed)
│
├── Planning/                        📁 Architecture & planning
│   ├── REFACTOR_PLAN.md             ← From root
│   └── roadmap.md                   (if needed)
│
├── Design/                          ✅ Keep as-is (already good)
│   ├── claude-cli-reference.md
│   ├── godot-server-spec.md
│   ├── security-baseline.md
│   ├── multi-framework-support.md
│   ├── performance-targets.md
│   ├── issue-workflow.md
│   ├── retry-logic.md
│   ├── phase0-validation.md
│   ├── phase1.1-multi-project.md
│   └── wizard-complete-spec.md
│
├── refactor/                        ✅ Keep as-is (v2.0 implementation docs)
│   ├── IMPLEMENTATION_CORE.md
│   ├── 01-architecture.md
│   ├── 02-database-schema.md
│   ├── 03-api-endpoints.md
│   ├── 04-webhooks.md
│   ├── 05-client-separation.md
│   ├── 06-implementation-timeline.md
│   ├── 07-migration-guide.md
│   ├── 08-testing-strategy.md
│   └── 09-api-guide.md
│
├── Archive/                         ✅ Keep as-is
│   ├── v1/                          (v1.x planning docs)
│   │   ├── README.md
│   │   ├── game-dev-automation-plan-v2.md
│   │   ├── implementation-roadmap.md
│   │   └── wizard-overview.md
│   │
│   └── v2-migration/                📁 v2.0 migration artifacts (NEW)
│       ├── PHASE0_UI_SUMMARY.md     ← From root
│       └── WORKFLOW_FIXES_REPORT.md ← From root
│
└── meta/                            📁 Documentation metadata (NEW)
    └── DOCS_AUDIT.md                ← From root
```

---

## 🚚 Systems to Move to Other Repos

### 1. Web UI → lazy-bird-ui Repository

**What to Move:**
```
web/                                 → lazy-bird-ui/
├── backend/                         → Should NOT move (keep Flask API)
│   ├── app.py                       → Keep in lazy-bird (Flask wrapper for FastAPI)
│   ├── api/                         → Keep (Flask routes)
│   └── services/                    → Keep (business logic)
│
└── frontend/                        → Move to lazy-bird-ui
    ├── src/                         → lazy-bird-ui/src/
    ├── public/                      → lazy-bird-ui/public/
    ├── package.json                 → lazy-bird-ui/package.json
    ├── vite.config.ts               → lazy-bird-ui/vite.config.ts
    └── README.md                    → lazy-bird-ui/README.md
```

**WAIT! Re-reading the architecture...**

Actually, looking at the SETUP_COMPLETE.md and the architecture docs, the Web UI should be:

**Option A: Keep web/ in lazy-bird (current monorepo approach)**
- Current README says: "Part of lazy-bird core (monorepo structure)"
- Flask backend wraps FastAPI
- React frontend is built into Flask static files

**Option B: Split to lazy-bird-ui (microservice approach)**
- Standalone React app
- Calls lazy-bird FastAPI directly
- Separate deployment

**Need to clarify with user which approach they want.**

### 2. Setup Files → Respective Repos

**Move to lazy-bird-ui:**
```
.github/repos-setup/lazy-bird-ui/
├── IMPLEMENTATION.md                → lazy-bird-ui/IMPLEMENTATION.md
└── README.md                        → Merge into lazy-bird-ui/README.md
```

**Move to plane-lazy-bird-integration:**
```
.github/repos-setup/plane-lazy-bird-integration/
├── IMPLEMENTATION.md                → plane-lazy-bird-integration/IMPLEMENTATION.md
└── README.md                        → Merge into plane-lazy-bird-integration/README.md
```

**Keep in lazy-bird:**
```
.github/repos-setup/
├── REPOSITORY_SETUP.md              ✅ Keep (historical)
├── NEXT_STEPS.md                    ✅ Keep (coordination)
└── SETUP_COMPLETE.md                ✅ Keep (status)
```

### 3. Symlink to Remove

**Delete:**
```
lazy_bird/web/ → ../web              ❌ Remove (causes circular reference)
```

This symlink was meant to make web/ accessible from the package, but it creates a symlink loop and is not needed.

---

## 📊 Summary: What Stays in lazy-bird Core

### ✅ Systems That Belong Here

**Core Application:**
- ✅ `lazy_bird/` - Main Python package
  - `api/` - FastAPI routes
  - `core/` - Core business logic
  - `models/` - SQLAlchemy models
  - `schemas/` - Pydantic schemas
  - `services/` - Service layer
  - `tasks/` - Celery tasks
  - `cli.py` - CLI entry point

**Automation Scripts:**
- ✅ `scripts/` - Core automation
  - `agent-runner.sh` - Task executor
  - `issue-watcher.py` - GitHub monitor
  - `queue-processor.py` - Queue processor
  - `project-manager.py` - Project CLI

**Infrastructure:**
- ✅ `docker/` - Docker configs
- ✅ `systemd/` - systemd services
- ✅ `nginx/` - nginx configs
- ✅ `alembic/` - Database migrations
- ✅ `config/` - Configuration templates

**Testing:**
- ✅ `tests/` - Core test suite
  - Unit tests
  - Integration tests
  - E2E tests

**Documentation:**
- ✅ `Docs/` - All documentation (reorganized)

### ❓ Web UI - Need Clarification

**Current Status:**
- `web/backend/` - Flask API wrapper (7 files)
- `web/frontend/` - React app (full stack)

**Question for User:**
1. **Keep as monorepo** - web/ stays in lazy-bird, deployed together
2. **Split to microservice** - web/frontend/ moves to lazy-bird-ui, standalone deployment

**Recommendation:** Keep as monorepo for simplicity, since:
- Frontend is only ~50 files
- Backend is just a Flask wrapper (7 files)
- Easier deployment (single Docker image)
- Current README says "Part of lazy-bird core"

---

## 🎯 Action Plan

### Phase 1: Documentation Reorganization (This Session)

1. ✅ Create `Docs/README.md` (documentation hub)
2. ✅ Create subdirectories in Docs/
3. ✅ Move 10 root MD files to appropriate subdirectories
4. ✅ Update all internal links
5. ✅ Test that all links work

### Phase 2: Web UI Decision (Need User Input)

**Option A: Keep Monorepo (Recommended)**
- Keep `web/` in lazy-bird
- Remove `lazy_bird/web/` symlink
- Update documentation to clarify monorepo approach

**Option B: Split to Microservice**
- Move `web/frontend/` to lazy-bird-ui repo
- Keep `web/backend/` as thin API gateway
- Update deployment docs

### Phase 3: Setup Files Migration (Future)

- Move UI setup files to lazy-bird-ui when repo is ready
- Move Plane setup files when repo is ready
- Keep coordination files in lazy-bird

### Phase 4: Remove Symlink

```bash
rm lazy_bird/web
```

---

## 📝 Recommendations

1. **Immediate:** Reorganize documentation (Phase 1)
   - Low risk, high value
   - Makes repo cleaner immediately
   - All files stay in same repo

2. **Decide:** Web UI architecture (Phase 2)
   - User needs to confirm: monorepo or split?
   - Current docs suggest monorepo
   - Affects deployment strategy

3. **Future:** Move setup files when repos are populated
   - Low priority
   - Can wait until lazy-bird-ui and plane repos are active

4. **Cleanup:** Remove problematic symlink
   - Safe to do after confirming web/ location

---

## ❓ Questions for User

1. **Web UI Architecture:**
   - Should `web/` stay in lazy-bird core (monorepo)?
   - Or move `web/frontend/` to lazy-bird-ui (microservice)?
   - Current docs say "Part of lazy-bird core (monorepo structure)"

2. **Documentation Reorganization:**
   - Proceed with moving 10 root MD files to Docs/ subdirectories?
   - This will make the root much cleaner (15 files → 5 files)

3. **Setup Files:**
   - Keep .github/repos-setup/ files until other repos are ready?
   - Or move them now to empty repos?

---

**Status:** 📋 **Awaiting User Decision** on Web UI architecture and documentation reorganization approval
