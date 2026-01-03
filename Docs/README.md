# Lazy-Bird Documentation Hub

**Version:** 2.0 (Production Ready)
**Last Updated:** 2026-01-03

Welcome to the Lazy-Bird documentation! This README serves as the central navigation hub for all project documentation.

---

## 📚 Quick Navigation

### For New Users
- **[Installation Guide](Installation/INSTALL.md)** - Complete installation instructions
- **[Quick Start](Installation/SETUP_PROJECT.md)** - Get started in 10 minutes
- **[Main README](../README.md)** - Project overview and introduction

### For Developers
- **[Architecture Overview](refactor/01-architecture.md)** - System architecture
- **[API Documentation](API_GUIDE.md)** - Complete API reference
- **[Database Schema](refactor/02-database-schema.md)** - PostgreSQL schema design
- **[Contributing Guide](../CONTRIBUTING.md)** - How to contribute

### For Operations
- **[Deployment Guide](DEPLOYMENT.md)** - Production deployment
- **[Docker Setup](Operations/DOCKER.md)** - Container deployment
- **[Management Scripts](Operations/MANAGEMENT_SCRIPTS.md)** - Operational scripts

---

## 📖 Documentation Structure

```
Docs/
├── README.md                    ← You are here
│
├── Installation/                📁 Setup & Installation
│   ├── INSTALL.md               → Complete installation guide
│   └── SETUP_PROJECT.md         → Quick setup instructions
│
├── Operations/                  📁 Running & Managing the System
│   ├── DOCKER.md                → Docker deployment
│   └── MANAGEMENT_SCRIPTS.md    → Operational scripts reference
│
├── Testing/                     📁 Testing Documentation
│   ├── TEST_RESULTS_SUMMARY.md  → Historical test results
│   └── E2E_TEST_SUCCESS_SUMMARY.md → v2.0 E2E test validation
│
├── Planning/                    📁 Architecture & Planning
│   └── REFACTOR_PLAN.md         → v2.0 refactor plan (complete)
│
├── Design/                      📁 Design Specifications
│   ├── claude-cli-reference.md  → Claude CLI usage
│   ├── godot-server-spec.md     → Godot server design (Phase 2)
│   ├── security-baseline.md     → Security guidelines
│   ├── multi-framework-support.md → Framework support
│   ├── performance-targets.md   → Performance benchmarks
│   ├── issue-workflow.md        → GitHub/GitLab workflow
│   ├── retry-logic.md           → Test retry strategy
│   ├── phase0-validation.md     → Phase 0 validation
│   ├── phase1.1-multi-project.md → Multi-project support
│   └── wizard-complete-spec.md  → Setup wizard spec
│
├── refactor/                    📁 v2.0 Implementation Docs
│   ├── IMPLEMENTATION_CORE.md   → Week 1-3 detailed plan
│   ├── 01-architecture.md       → System architecture
│   ├── 02-database-schema.md    → PostgreSQL schema
│   ├── 03-api-endpoints.md      → API endpoints (30+)
│   ├── 04-webhooks.md           → Event system
│   ├── 05-client-separation.md  → Client extraction guide
│   ├── 06-implementation-timeline.md → Timeline
│   ├── 07-migration-guide.md    → v1.1 → v2.0 migration
│   ├── 08-testing-strategy.md   → Testing approach
│   └── 09-api-guide.md          → API usage guide
│
├── Archive/                     📁 Historical Documentation
│   ├── v1/                      → v1.x planning docs
│   │   ├── README.md            → Archive index
│   │   ├── game-dev-automation-plan-v2.md
│   │   ├── implementation-roadmap.md
│   │   └── wizard-overview.md
│   │
│   └── v2-migration/            → v2.0 migration artifacts
│       ├── PHASE0_UI_SUMMARY.md → Web UI completion
│       └── WORKFLOW_FIXES_REPORT.md → Phase 1.1 fixes
│
├── meta/                        📁 Documentation Metadata
│   └── DOCS_AUDIT.md            → Documentation audit results
│
├── API_GUIDE.md                 📄 Complete API documentation
└── DEPLOYMENT.md                📄 Production deployment guide
```

---

## 🎯 Documentation by Use Case

### "I want to install Lazy-Bird"
1. **[INSTALL.md](Installation/INSTALL.md)** - Full installation guide
2. **[SETUP_PROJECT.md](Installation/SETUP_PROJECT.md)** - Quick setup
3. **[DOCKER.md](Operations/DOCKER.md)** - Docker installation

### "I want to understand the architecture"
1. **[01-architecture.md](refactor/01-architecture.md)** - System overview
2. **[02-database-schema.md](refactor/02-database-schema.md)** - Database design
3. **[03-api-endpoints.md](refactor/03-api-endpoints.md)** - API structure
4. **[04-webhooks.md](refactor/04-webhooks.md)** - Event system

### "I want to deploy to production"
1. **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment guide
2. **[DOCKER.md](Operations/DOCKER.md)** - Docker deployment
3. **[security-baseline.md](Design/security-baseline.md)** - Security guidelines

### "I want to contribute code"
1. **[CONTRIBUTING.md](../CONTRIBUTING.md)** - Contribution guide
2. **[08-testing-strategy.md](refactor/08-testing-strategy.md)** - Testing approach
3. **[API_GUIDE.md](API_GUIDE.md)** - API reference

### "I want to migrate from v1.1 to v2.0"
1. **[07-migration-guide.md](refactor/07-migration-guide.md)** - Migration guide
2. **[REFACTOR_PLAN.md](Planning/REFACTOR_PLAN.md)** - What changed
3. **[CHANGELOG.md](../CHANGELOG.md)** - Version history

### "I want to run tests"
1. **[08-testing-strategy.md](refactor/08-testing-strategy.md)** - Testing guide
2. **[E2E_TEST_SUCCESS_SUMMARY.md](Testing/E2E_TEST_SUCCESS_SUMMARY.md)** - E2E test examples
3. **[TEST_RESULTS_SUMMARY.md](Testing/TEST_RESULTS_SUMMARY.md)** - Test results

### "I want to manage the system"
1. **[MANAGEMENT_SCRIPTS.md](Operations/MANAGEMENT_SCRIPTS.md)** - Scripts reference
2. **[API_GUIDE.md](API_GUIDE.md)** - API operations
3. **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production operations

---

## 🔍 Finding Documentation

### By Topic

**Installation & Setup**
- [INSTALL.md](Installation/INSTALL.md) - Full installation
- [SETUP_PROJECT.md](Installation/SETUP_PROJECT.md) - Quick setup
- [wizard-complete-spec.md](Design/wizard-complete-spec.md) - Setup wizard

**Architecture & Design**
- [01-architecture.md](refactor/01-architecture.md) - System architecture
- [02-database-schema.md](refactor/02-database-schema.md) - Database design
- [05-client-separation.md](refactor/05-client-separation.md) - Multi-repo structure

**API & Integration**
- [API_GUIDE.md](API_GUIDE.md) - Complete API reference
- [03-api-endpoints.md](refactor/03-api-endpoints.md) - Endpoint specifications
- [04-webhooks.md](refactor/04-webhooks.md) - Webhook system

**Deployment & Operations**
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment
- [DOCKER.md](Operations/DOCKER.md) - Docker setup
- [MANAGEMENT_SCRIPTS.md](Operations/MANAGEMENT_SCRIPTS.md) - Operations

**Testing & Quality**
- [08-testing-strategy.md](refactor/08-testing-strategy.md) - Testing approach
- [E2E_TEST_SUCCESS_SUMMARY.md](Testing/E2E_TEST_SUCCESS_SUMMARY.md) - E2E tests
- [TEST_RESULTS_SUMMARY.md](Testing/TEST_RESULTS_SUMMARY.md) - Test results

**Security**
- [security-baseline.md](Design/security-baseline.md) - Security guidelines

**Framework Support**
- [multi-framework-support.md](Design/multi-framework-support.md) - 18+ frameworks
- [phase1.1-multi-project.md](Design/phase1.1-multi-project.md) - Multi-project

---

## 📊 Documentation Status

### ✅ Production Ready (v2.0)
- All core documentation updated for v2.0
- E2E test validation complete
- Migration guides available
- API documentation complete

### 📋 Current Documentation Coverage
- **Installation**: Complete
- **Architecture**: Complete
- **API Reference**: Complete
- **Testing**: Complete
- **Deployment**: Complete
- **Operations**: Complete
- **Migration**: Complete

### 🚧 Future Additions
- Phase 2: Multi-agent documentation
- Advanced performance tuning
- Enterprise deployment patterns
- Video tutorials

---

## 🔗 External Resources

### Related Repositories
- **[lazy-bird](https://github.com/yusufkaraaslan/lazy-bird)** - Core engine (this repo)
- **[lazy-bird-ui](https://github.com/yusufkaraaslan/lazy-bird-ui)** - Web UI client
- **[plane-lazy-bird-integration](https://github.com/yusufkaraaslan/plane-lazy-bird-integration)** - Plane integration

### Community
- **Issues**: [GitHub Issues](https://github.com/yusufkaraaslan/lazy-bird/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yusufkaraaslan/lazy-bird/discussions)
- **Contributing**: [CONTRIBUTING.md](../CONTRIBUTING.md)

---

## 📝 Documentation Guidelines

### For Contributors

When adding new documentation:

1. **Location**: Choose the appropriate subdirectory
   - Installation docs → `Installation/`
   - Operations guides → `Operations/`
   - Test docs → `Testing/`
   - Planning docs → `Planning/`
   - Design specs → `Design/`

2. **Format**: Use Markdown with clear headers
3. **Links**: Use relative paths from document location
4. **Status**: Add status headers (e.g., "Status: ✅ Current")
5. **Updates**: Update this README.md when adding new docs

### Documentation Standards

- **Headers**: Use `#` for title, `##` for sections
- **Code Blocks**: Always specify language (```python, ```bash)
- **Links**: Relative paths preferred
- **Examples**: Include practical examples
- **Status**: Mark with ✅ (current), 📋 (planned), or 🚧 (in progress)

---

## ❓ Need Help?

**Can't find what you're looking for?**

1. **Check the main README**: [../README.md](../README.md)
2. **Search the docs**: Use GitHub search within `/Docs`
3. **Ask in Discussions**: [GitHub Discussions](https://github.com/yusufkaraaslan/lazy-bird/discussions)
4. **Report missing docs**: [Open an issue](https://github.com/yusufkaraaslan/lazy-bird/issues)

---

**Last Updated**: 2026-01-03
**Documentation Version**: v2.0
**Status**: ✅ Production Ready
