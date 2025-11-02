# Multi-Framework Support Design

## Overview

Transform Lazy_Bird from a Godot-specific automation system to a **framework-agnostic development automation platform** that works with any programming language, framework, or game engine.

## Goals

1. **Universal Automation** - Support any development project (games, web, backend, CLI tools)
2. **Easy Configuration** - Select framework during wizard setup
3. **Consistent Workflow** - Same GitHub Issue → PR workflow for all frameworks
4. **Framework Templates** - Pre-configured settings for popular frameworks

## Supported Frameworks (Initial)

### Game Engines
- **Godot** - GDScript, gdUnit4 tests, headless mode
- **Unity** - C#, NUnit tests, headless mode
- **Unreal** - C++/Blueprint, Automation tests
- **Bevy** - Rust, cargo test

### Backend Frameworks
- **Django** - Python, pytest, manage.py test
- **Flask** - Python, pytest
- **Express** - Node.js, Jest/Mocha
- **FastAPI** - Python, pytest
- **Rails** - Ruby, RSpec

### Frontend Frameworks
- **React** - JavaScript/TypeScript, Jest
- **Vue** - JavaScript/TypeScript, Vitest
- **Angular** - TypeScript, Karma/Jest
- **Svelte** - JavaScript/TypeScript, Vitest

### Programming Languages (General)
- **Python** - pytest, unittest
- **Node.js** - npm test, Jest
- **Rust** - cargo test, cargo build
- **Go** - go test, go build
- **C/C++** - make test, CMake
- **Java** - Maven/Gradle tests

## Configuration Schema

### Enhanced config.yml

```yaml
# Project Configuration
project:
  type: godot                    # Framework identifier
  name: "My Awesome Game"
  path: /home/user/my-project
  language: gdscript             # Primary language

# Framework-Specific Settings
framework:
  godot:
    version: "4.2"
    test_framework: gdUnit4
    test_command: "godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --test-suite all"
    build_command: null          # Not needed for Godot

  python:
    version: "3.11"
    test_framework: pytest
    test_command: "pytest tests/ -v"
    build_command: null

  rust:
    version: "1.75"
    test_framework: cargo
    test_command: "cargo test"
    build_command: "cargo build --release"

  nodejs:
    version: "20"
    test_framework: jest
    test_command: "npm test"
    build_command: "npm run build"

# Active Framework Configuration
test_command: "godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --test-suite all"
build_command: null
lint_command: null               # Optional linting
format_command: null             # Optional formatting

# Git Configuration (framework-agnostic)
git_platform: github
repository: https://github.com/user/repo

# Automation Configuration (framework-agnostic)
phase: 1
max_concurrent_agents: 1
agent_max_ram_gb: 8
poll_interval_seconds: 60
```

## Wizard Changes

### New Question Flow (9 questions instead of 8)

```bash
❓ [1/9] What type of project are you working on?
  1) Game Engine
  2) Backend Framework
  3) Frontend Framework
  4) Programming Language (General)
  5) Other/Custom

# If Game Engine selected:
❓ [1b/9] Which game engine?
  1) Godot
  2) Unity
  3) Unreal Engine
  4) Bevy (Rust)
  5) Other (manual config)

# If Backend Framework selected:
❓ [1b/9] Which backend framework?
  1) Django (Python)
  2) Flask (Python)
  3) FastAPI (Python)
  4) Express (Node.js)
  5) Rails (Ruby)
  6) Other (manual config)

# Continue with existing questions...
❓ [2/9] Enter your project path: /home/user/my-project
❓ [3/9] Which git platform? (GitHub/GitLab)
...
```

### Framework Presets

```python
# In wizard.sh or Python config generator

FRAMEWORK_PRESETS = {
    "godot": {
        "test_command": "godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --test-suite all",
        "build_command": None,
        "file_extensions": [".gd", ".tscn", ".tres"],
        "ignore_patterns": [".godot/", ".import/"],
    },
    "python-pytest": {
        "test_command": "pytest tests/ -v --cov",
        "build_command": None,
        "lint_command": "flake8 .",
        "format_command": "black .",
        "file_extensions": [".py"],
        "ignore_patterns": ["__pycache__/", ".pytest_cache/", "venv/"],
    },
    "rust": {
        "test_command": "cargo test --all",
        "build_command": "cargo build --release",
        "lint_command": "cargo clippy",
        "format_command": "cargo fmt",
        "file_extensions": [".rs"],
        "ignore_patterns": ["target/", "Cargo.lock"],
    },
    "nodejs-jest": {
        "test_command": "npm test",
        "build_command": "npm run build",
        "lint_command": "npm run lint",
        "file_extensions": [".js", ".ts", ".jsx", ".tsx"],
        "ignore_patterns": ["node_modules/", "dist/", "build/"],
    },
    "django": {
        "test_command": "python manage.py test",
        "build_command": None,
        "lint_command": "flake8 .",
        "file_extensions": [".py"],
        "ignore_patterns": ["__pycache__/", "*.pyc", "db.sqlite3"],
    },
    "unity": {
        "test_command": "unity-editor -runTests -testPlatform EditMode -testResults test-results.xml",
        "build_command": "unity-editor -quit -batchmode -buildTarget StandaloneLinux64",
        "file_extensions": [".cs", ".unity", ".prefab"],
        "ignore_patterns": ["Library/", "Temp/", "obj/"],
    },
}
```

## Agent Runner Changes

### Current (Godot-specific)

```bash
# In agent-runner.sh
run_claude() {
    # ... claude execution ...
}

check_changes() {
    # Generic git checks - ALREADY FRAMEWORK-AGNOSTIC ✓
}

run_tests() {
    # HARDCODED: Godot-specific tests
    godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --test-suite all
}

create_pr() {
    # Generic PR creation - ALREADY FRAMEWORK-AGNOSTIC ✓
}
```

### New (Framework-agnostic)

```bash
# In agent-runner.sh
run_tests() {
    log_info "Running tests..."

    # Read test command from config
    TEST_CMD=$(grep "^test_command:" ~/.config/lazy_birtd/config.yml | sed 's/test_command: *//' | tr -d '"')

    if [ -z "$TEST_CMD" ] || [ "$TEST_CMD" = "null" ]; then
        log_warning "No test command configured, skipping tests"
        return 0
    fi

    log_info "Test command: $TEST_CMD"

    # Execute tests
    if eval "$TEST_CMD" > "$LOG_DIR/test-output.log" 2>&1; then
        log_success "Tests passed"
        return 0
    else
        log_error "Tests failed"
        cat "$LOG_DIR/test-output.log"
        return 1
    fi
}

run_build() {
    log_info "Running build (if configured)..."

    # Read build command from config
    BUILD_CMD=$(grep "^build_command:" ~/.config/lazy_birtd/config.yml | sed 's/build_command: *//' | tr -d '"')

    if [ -z "$BUILD_CMD" ] || [ "$BUILD_CMD" = "null" ]; then
        log_info "No build command configured, skipping build"
        return 0
    fi

    log_info "Build command: $BUILD_CMD"

    # Execute build
    if eval "$BUILD_CMD" > "$LOG_DIR/build-output.log" 2>&1; then
        log_success "Build succeeded"
        return 0
    else
        log_error "Build failed"
        cat "$LOG_DIR/build-output.log"
        return 1
    fi
}
```

## Phase 0 Validation Changes

### Current (Godot-specific)

```bash
# validate-all.sh checks for:
- Claude CLI ✓ (framework-agnostic)
- Godot installation ✗ (Godot-specific)
- gdUnit4 ✗ (Godot-specific)
- Git worktrees ✓ (framework-agnostic)
```

### New (Framework-agnostic)

```bash
# validate-all.sh
#!/bin/bash
# Framework-agnostic validation

validate_claude() {
    # Check Claude CLI (unchanged)
}

validate_git() {
    # Check git and worktrees (unchanged)
}

validate_framework() {
    # Read project type from argument or config
    PROJECT_TYPE=${1:-"generic"}

    case $PROJECT_TYPE in
        godot)
            validate_godot
            ;;
        python)
            validate_python
            ;;
        rust)
            validate_rust
            ;;
        nodejs)
            validate_nodejs
            ;;
        *)
            log_info "No framework-specific validation for: $PROJECT_TYPE"
            ;;
    esac
}

validate_godot() {
    command -v godot &> /dev/null || return 1
    [ -d "$PROJECT_PATH/addons/gdUnit4" ] || return 1
}

validate_python() {
    command -v python3 &> /dev/null || return 1
    command -v pip3 &> /dev/null || return 1
}

validate_rust() {
    command -v cargo &> /dev/null || return 1
    [ -f "$PROJECT_PATH/Cargo.toml" ] || return 1
}

validate_nodejs() {
    command -v node &> /dev/null || return 1
    command -v npm &> /dev/null || return 1
    [ -f "$PROJECT_PATH/package.json" ] || return 1
}
```

## Migration Path

### For Existing Godot Users

```bash
# Existing config.yml will continue to work
# But now they can optionally add:
project:
  type: godot

# And future configs will use the new format
```

### For New Users

```bash
# Wizard will ask project type first
# Then configure everything automatically
./wizard.sh

# Prompts:
# - Project type? (Godot/Python/Rust/Node.js/etc.)
# - Auto-detects framework if possible
# - Configures test/build commands automatically
```

## Benefits

### 1. **Broader Appeal**
- Web developers can use it
- Backend engineers can use it
- Systems programmers can use it
- Not just game devs!

### 2. **Same Workflow**
- GitHub Issues → Automation → PRs
- Works identically across frameworks
- Learn once, use everywhere

### 3. **Easy Switching**
- Work on multiple projects
- Same tool for all of them
- Consistent experience

### 4. **More Examples**
```bash
# Game Development
gh issue create --label "ready" --title "Add player jump"

# Web Development
gh issue create --label "ready" --title "Add user login endpoint"

# Systems Programming
gh issue create --label "ready" --title "Optimize sorting algorithm"

# All use same automation!
```

## Implementation Plan

### Phase 1a: Make Core Framework-Agnostic (2-3 hours)

1. **Update config schema** (30 min)
   - Add `project.type` field
   - Add framework-specific sections
   - Add `test_command`, `build_command` fields
   - Keep backward compatibility

2. **Update wizard.sh** (1 hour)
   - Add project type selection (Q1)
   - Add framework presets
   - Generate framework-specific config

3. **Update agent-runner.sh** (1 hour)
   - Replace hardcoded Godot commands
   - Read from config instead
   - Add build command support

4. **Update Phase 0 validation** (30 min)
   - Make framework detection optional
   - Add per-framework validators

### Phase 1b: Add Framework Presets (1-2 hours per framework)

1. **Python preset** - pytest, black, flake8
2. **Node.js preset** - Jest, npm scripts
3. **Rust preset** - cargo test, cargo build
4. **More as needed**

### Phase 2: Enhanced Features (Future)

- Framework-specific task templates
- Better test parsing per framework
- Framework-specific cost estimates
- Community presets repository

## Example Configs

### Godot Project
```yaml
project:
  type: godot
  name: "My Platformer"
  path: /home/user/platformer

test_command: "godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --test-suite all"
build_command: null
```

### Python/Django Project
```yaml
project:
  type: django
  name: "My Web App"
  path: /home/user/webapp

test_command: "python manage.py test"
build_command: null
lint_command: "flake8 ."
```

### Rust Project
```yaml
project:
  type: rust
  name: "My CLI Tool"
  path: /home/user/cli-tool

test_command: "cargo test --all"
build_command: "cargo build --release"
lint_command: "cargo clippy"
```

### Node.js/React Project
```yaml
project:
  type: react
  name: "My Dashboard"
  path: /home/user/dashboard

test_command: "npm test"
build_command: "npm run build"
lint_command: "npm run lint"
```

## Documentation Updates

### README.md
- Update title: "Automate ANY development project while you sleep"
- Update examples to show multiple frameworks
- Add "Supported Frameworks" section

### CLAUDE.md
- Add framework selection guidance
- Update examples for multiple languages
- Add framework-specific best practices

## Backward Compatibility

All existing Godot configurations will continue to work:
- If `project.type` is missing, assume Godot
- If `test_command` is missing, use Godot default
- Migration is optional, not required

## Conclusion

This change transforms Lazy_Bird from a **niche Godot tool** into a **universal development automation platform**. The core workflow (Issues → Automation → PRs) remains the same, but now works for any project type.

**Impact:**
- 10x larger potential user base
- Same codebase, more applications
- Minimal implementation effort
- Huge value increase

**Next Steps:**
1. Get user approval for this direction
2. Implement Phase 1a (core changes)
3. Test with 2-3 different frameworks
4. Update documentation
5. Release as v2.2 (Multi-Framework Support)
