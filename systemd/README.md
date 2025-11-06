# Systemd Services for Lazy_Bird

This directory contains systemd service files for running Lazy_Bird components as system services.

## Services

### issue-watcher.service

Monitors GitHub/GitLab for issues labeled "ready" and queues them for processing.

### godot-server.service

Runs the HTTP API server that coordinates Godot test execution between multiple agents.

## Installation

### User Service (Recommended for Development)

```bash
# Create systemd user directory
mkdir -p ~/.config/systemd/user/

# Copy service file
cp systemd/issue-watcher.service ~/.config/systemd/user/

# Edit service file to use your actual paths
nano ~/.config/systemd/user/issue-watcher.service

# Reload systemd
systemctl --user daemon-reload

# Enable service to start on login
systemctl --user enable issue-watcher

# Start service
systemctl --user start issue-watcher

# Check status
systemctl --user status issue-watcher

# View logs
journalctl --user -u issue-watcher -f
```

### System Service (For Production/Always-Running)

```bash
# Copy service file
sudo cp systemd/issue-watcher.service /etc/systemd/system/

# Edit service file (change User and paths)
sudo nano /etc/systemd/system/issue-watcher.service

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable issue-watcher

# Start service
sudo systemctl start issue-watcher

# Check status
sudo systemctl status issue-watcher

# View logs
sudo journalctl -u issue-watcher -f
```

## Prerequisites

Before starting the service:

1. **Configuration file** must exist:
   ```bash
   mkdir -p ~/.config/lazy_birtd/secrets
   mkdir -p ~/.config/lazy_birtd/data

   # Copy example config
   cp config/config.example.yml ~/.config/lazy_birtd/config.yml

   # Edit configuration
   nano ~/.config/lazy_birtd/config.yml
   ```

2. **API token** must be configured:
   ```bash
   # For GitHub
   echo "YOUR_GITHUB_TOKEN" > ~/.config/lazy_birtd/secrets/github_token
   chmod 600 ~/.config/lazy_birtd/secrets/github_token

   # For GitLab
   echo "YOUR_GITLAB_TOKEN" > ~/.config/lazy_birtd/secrets/gitlab_token
   chmod 600 ~/.config/lazy_birtd/secrets/gitlab_token
   ```

3. **Python dependencies** must be installed:
   ```bash
   pip3 install requests pyyaml
   ```

## Creating GitHub/GitLab Tokens

### GitHub Personal Access Token

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a descriptive name: "Lazy_Bird Issue Watcher"
4. Select scopes:
   - `repo` (Full control of private repositories)
   - `workflow` (Update GitHub Action workflows)
5. Click "Generate token"
6. Copy token immediately (you won't see it again)
7. Save to `~/.config/lazy_birtd/secrets/github_token`

### GitLab Personal Access Token

1. Go to: https://gitlab.com/-/profile/personal_access_tokens
2. Give it a name: "Lazy_Bird Issue Watcher"
3. Select scopes:
   - `api` (Access the authenticated user's API)
   - `read_repository` (Read repository)
   - `write_repository` (Write repository)
4. Click "Create personal access token"
5. Copy token immediately
6. Save to `~/.config/lazy_birtd/secrets/gitlab_token`

## Management Commands

```bash
# Start service
systemctl --user start issue-watcher

# Stop service
systemctl --user stop issue-watcher

# Restart service
systemctl --user restart issue-watcher

# Check if service is running
systemctl --user is-active issue-watcher

# View status and recent logs
systemctl --user status issue-watcher

# View full logs
journalctl --user -u issue-watcher

# Follow logs in real-time
journalctl --user -u issue-watcher -f

# View logs from last 1 hour
journalctl --user -u issue-watcher --since "1 hour ago"
```

## Troubleshooting

### Service won't start

```bash
# Check for errors
journalctl --user -u issue-watcher -n 50

# Common issues:
# 1. Config file missing
ls -la ~/.config/lazy_birtd/config.yml

# 2. API token missing
ls -la ~/.config/lazy_birtd/secrets/

# 3. Python dependencies missing
python3 -c "import requests, yaml"

# 4. Permissions wrong
chmod 700 ~/.config/lazy_birtd/secrets
chmod 600 ~/.config/lazy_birtd/secrets/*
```

### Issues not being detected

```bash
# Test API connection manually
python3 scripts/issue-watcher.py

# Check GitHub/GitLab for:
# - Issue has "ready" label
# - Token has correct permissions
# - Repository name is correct in config

# Verify token works
# For GitHub:
curl -H "Authorization: token $(cat ~/.config/lazy_birtd/secrets/github_token)" \
     https://api.github.com/user

# For GitLab:
curl -H "PRIVATE-TOKEN: $(cat ~/.config/lazy_birtd/secrets/gitlab_token)" \
     https://gitlab.com/api/v4/user
```

### Service crashes or restarts frequently

```bash
# Check system resources
free -h
df -h

# View crash logs
journalctl --user -u issue-watcher --since today | grep -i error

# Increase restart delay in service file
# RestartSec=30 -> RestartSec=60
```

## Uninstallation

```bash
# Stop and disable service
systemctl --user stop issue-watcher
systemctl --user disable issue-watcher

# Remove service file
rm ~/.config/systemd/user/issue-watcher.service

# Reload systemd
systemctl --user daemon-reload

# Optionally remove configuration
# rm -rf ~/.config/lazy_birtd
```

## Security Notes

- API tokens are stored in `~/.config/lazy_birtd/secrets/` with 600 permissions
- Never commit tokens to git (check `.gitignore`)
- Rotate tokens every 90 days
- Use minimal required permissions for tokens
- Review service logs regularly for suspicious activity
