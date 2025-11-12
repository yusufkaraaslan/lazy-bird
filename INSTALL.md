# 📦 Installation Guide

Lazy_Bird can be installed via pip, UV, or directly from source.

## Quick Install Methods

### 🚀 Method 1: Install with pip (Recommended)

```bash
# Install from PyPI (when published)
pip install lazy-bird

# Install with web UI support
pip install lazy-bird[web]

# Install with development dependencies
pip install lazy-bird[dev]

# Install everything
pip install lazy-bird[all]
```

### ⚡ Method 2: Install with UV (Fast & Modern)

[UV](https://github.com/astral-sh/uv) is a blazingly fast Python package installer.

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install lazy-bird with UV
uv pip install lazy-bird

# Install with extras
uv pip install "lazy-bird[web,dev]"
```

### 🔧 Method 3: Install from GitHub

```bash
# Install latest release
pip install git+https://github.com/yusufkaraaslan/lazy-bird.git@v0.1.0

# Install from main branch (bleeding edge)
pip install git+https://github.com/yusufkaraaslan/lazy-bird.git

# With UV
uv pip install git+https://github.com/yusufkaraaslan/lazy-bird.git@v0.1.0
```

### 💻 Method 4: Install from Source (Development)

```bash
# Clone repository
git clone https://github.com/yusufkaraaslan/lazy-bird.git
cd lazy-bird

# Install in editable mode
pip install -e .

# Or with extras
pip install -e ".[all]"

# With UV
uv pip install -e ".[all]"
```

## Verify Installation

```bash
# Check version
lazy-bird --version

# Show help
lazy-bird --help

# Check status
lazy-bird status
```

## CLI Commands

After installation, you'll have these commands available:

| Command | Description |
|---------|-------------|
| `lazy-bird` | Main CLI interface |
| `lazy-bird setup` | Run setup wizard |
| `lazy-bird server` | Start web backend |
| `lazy-bird status` | Show system status |
| `lazy-bird godot` | Run Godot test server |
| `lazy-bird watch` | Run issue watcher |
| `lazy-bird project` | Manage projects |

## Usage Examples

### Run Setup Wizard

```bash
# Interactive setup
lazy-bird setup

# Check status
lazy-bird setup --status

# Run health checks
lazy-bird setup --health
```

### Start Web Server

```bash
# Default (localhost:5000)
lazy-bird server

# Custom host and port
lazy-bird server --host 0.0.0.0 --port 8080

# Or use the direct command
lazy-bird-server
```

### Manage Projects

```bash
# List projects
lazy-bird project list

# Add project
lazy-bird project add /path/to/project

# Enable/disable project
lazy-bird project enable my-project
lazy-bird project disable my-project
```

### Start Services

```bash
# Start Godot test server
lazy-bird godot

# Start issue watcher
lazy-bird watch

# Or use direct commands
lazy-bird-godot
lazy-bird-watcher
```

## System Requirements

### Minimum Requirements

- **OS**: Linux (Ubuntu 20.04+, Debian 11+, Fedora 35+, Arch-based) or Windows 10/11 with WSL2
- **Python**: 3.8 or higher
- **RAM**: 8GB minimum
- **CPU**: 4 cores minimum
- **Disk**: 20GB free space

### Recommended Requirements

- **RAM**: 16GB+ (for multi-agent Phase 2+)
- **CPU**: 8+ cores
- **Disk**: 50GB+ free space
- **OS**: Linux (native Docker support)

## Dependencies

### Python Dependencies (Auto-installed)

- Flask >= 3.0.0
- Flask-CORS >= 4.0.0
- psutil >= 5.9.6
- PyYAML >= 6.0.1
- requests >= 2.31.0
- python-dateutil >= 2.8.2

### System Dependencies (Install Manually)

**Required:**
- Git 2.30+
- Claude Code CLI (from Anthropic)
- Docker (for Phase 1+)

**Optional (framework-specific):**
- Godot 4.2+ (for game development)
- Node.js 18+ (for frontend projects)
- Rust toolchain (for Rust projects)
- Unity Hub (for Unity projects)

## Installing System Dependencies

### Ubuntu/Debian

```bash
# Update package list
sudo apt update

# Install Git and Docker
sudo apt install git docker.io docker-compose

# Add user to docker group
sudo usermod -aG docker $USER

# Install Node.js (for frontend)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs

# Install Claude Code CLI
# Follow: https://docs.anthropic.com/claude/docs/claude-code-installation
```

### Fedora/RHEL

```bash
# Install Git and Docker
sudo dnf install git docker docker-compose

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER

# Install Node.js
sudo dnf install nodejs npm
```

### Arch Linux/Manjaro

```bash
# Install Git and Docker
sudo pacman -S git docker docker-compose

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER

# Install Node.js
sudo pacman -S nodejs npm
```

### macOS

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install git docker node

# Install Docker Desktop for Mac
brew install --cask docker
```

## Framework-Specific Setup

### For Godot Projects

```bash
# Download Godot 4.2+ headless
wget https://github.com/godotengine/godot/releases/download/4.2-stable/Godot_v4.2-stable_linux_headless.64.zip
unzip Godot_v4.2-stable_linux_headless.64.zip -d ~/.local/bin/
chmod +x ~/.local/bin/godot

# Verify installation
godot --version
```

### For Unity Projects

```bash
# Install Unity Hub
# Follow: https://unity.com/download

# Install required Unity version via Hub
# License activation required
```

### For Python Projects

```bash
# Already have Python from main installation
# Install testing framework
pip install pytest pytest-cov

# Or use project-specific requirements
cd your-project
pip install -r requirements.txt
```

### For Rust Projects

```bash
# Install Rust toolchain
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Verify installation
rustc --version
cargo --version
```

### For Node.js/React Projects

```bash
# Node.js already installed
# Verify versions
node --version
npm --version

# Install project dependencies
cd your-project
npm install
```

## Troubleshooting

### Command not found: lazy-bird

```bash
# Make sure pip bin directory is in PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Or for UV installations
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Import errors

```bash
# Reinstall with all dependencies
pip install --force-reinstall lazy-bird[all]

# Or with UV
uv pip install --force-reinstall lazy-bird[all]
```

### Permission denied for Docker

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and log back in for changes to take effect
# Or run this in current terminal
newgrp docker
```

### Frontend not building

```bash
# Install Node.js dependencies manually
cd web/frontend
npm install
npm run build
```

## Next Steps

After installation:

1. **Run setup wizard**: `lazy-bird setup`
2. **Read documentation**: Check `CLAUDE.md` and `README.md`
3. **Start web UI**: `lazy-bird server`
4. **Create first task**: Follow Quick Start guide
5. **Join community**: GitHub Discussions

## Uninstall

```bash
# Uninstall with pip
pip uninstall lazy-bird

# Or with UV
uv pip uninstall lazy-bird

# Remove configuration (optional)
rm -rf ~/.config/lazy_bird
```

## Support

- **Documentation**: [CLAUDE.md](CLAUDE.md)
- **Issues**: [GitHub Issues](https://github.com/yusufkaraaslan/lazy-bird/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yusufkaraaslan/lazy-bird/discussions)

---

**Ready to automate your development? Start with `lazy-bird setup`!** 🦜💤
