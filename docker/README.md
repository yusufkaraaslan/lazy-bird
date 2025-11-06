# Docker Configuration for Lazy_Bird

This directory contains Docker configurations for running Lazy_Bird components in containerized environments.

## Images

### 1. Claude Agent (`claude-agent`)

Provides a secure, isolated environment for running Claude Code agents with support for multiple frameworks.

**Includes:**
- Ubuntu 22.04 base
- Python 3 + common packages (pytest, black, flake8)
- Node.js + npm
- Rust + Cargo (optional)
- Go (optional)
- Godot 4.2+ (headless mode)
- Build tools (gcc, cmake, make)

**Security Features:**
- Non-root user execution
- Resource limits (CPU, memory)
- Read-only root filesystem (configurable)
- No new privileges
- Isolated network

### 2. Godot Server (`godot-server`)

Runs the test coordination HTTP API server.

**Features:**
- Flask-based HTTP API
- Sequential test execution
- Job queue management
- Result parsing and storage

## Building Images

### Build All Images
```bash
cd docker
docker-compose build
```

### Build Specific Image
```bash
# Claude agent
docker build -t lazy-bird/claude-agent:latest ./claude-agent

# Godot server
docker build -t lazy-bird/godot-server:latest -f claude-agent/Dockerfile .
```

### Build with Custom Godot Version
```bash
docker build --build-arg GODOT_VERSION=4.3.0 -t lazy-bird/claude-agent:latest ./claude-agent
```

## Running Services

### Start Godot Server
```bash
cd docker
docker-compose up -d godot-server
```

### Check Status
```bash
docker-compose ps
docker-compose logs -f godot-server
```

### Stop Services
```bash
docker-compose down
```

## Running Individual Agent

Agents are typically spawned by `agent-runner.sh`, but you can run one manually:

```bash
docker run --rm -it \
  -v /tmp/agents/agent-42:/workspace \
  -v ~/.config/lazy_birtd:/home/agent/.config/lazy_birtd:ro \
  --memory=4g \
  --cpus=2 \
  --user 1000:1000 \
  lazy-bird/claude-agent:latest \
  claude -p "Implement feature from issue #42"
```

## Configuration

### Environment Variables

**For Godot Server:**
- `GODOT_SERVER_HOST` - Host to bind to (default: 127.0.0.1)
- `GODOT_SERVER_PORT` - Port to listen on (default: 5000)

**For Claude Agent:**
- `CLAUDE_API_KEY` - Claude API key (loaded from secrets)
- `GITHUB_TOKEN` - GitHub API token
- `GITLAB_TOKEN` - GitLab API token

### Volume Mounts

**Godot Server:**
- `/scripts` - Lazy_Bird scripts (read-only)
- `/var/lib/lazy_birtd/tests` - Test artifacts

**Claude Agent:**
- `/tmp/agents` - Git worktrees for tasks
- `/home/agent/.config/lazy_birtd` - Configuration (read-only)

## Resource Limits

### Recommended Limits (per agent)
- **Memory:** 4GB limit, 2GB reservation
- **CPU:** 2 cores
- **Disk:** 10GB (for worktree + artifacts)

### Adjust Limits
Edit `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 8G
```

## Security Best Practices

### 1. Use Non-Root User
Already configured in Dockerfile:
```dockerfile
USER agent
```

### 2. Limit Network Access
Bind services to localhost only:
```yaml
ports:
  - "127.0.0.1:5000:5000"
```

### 3. Mount Secrets Read-Only
```yaml
volumes:
  - ~/.config/lazy_birtd/secrets:/secrets:ro
```

### 4. Scan Images Regularly
```bash
# Install trivy
sudo apt-get install trivy

# Scan image
trivy image lazy-bird/claude-agent:latest
```

### 5. Keep Images Updated
```bash
# Rebuild with latest base image
docker-compose build --pull --no-cache
```

## Troubleshooting

### Godot Server Won't Start
```bash
# Check logs
docker-compose logs godot-server

# Common issues:
# 1. Port 5000 already in use
sudo lsof -i :5000

# 2. Volume permissions
sudo chown -R $(id -u):$(id -g) /var/lib/lazy_birtd

# 3. Godot not found in image
docker run --rm lazy-bird/godot-server:latest godot --version
```

### Agent Container Fails
```bash
# Check resource usage
docker stats

# Check container logs
docker logs <container-id>

# Verify volume mounts
docker inspect <container-id> | grep Mounts -A 20
```

### Network Issues
```bash
# Check network
docker network ls
docker network inspect lazy-bird-network

# Test connectivity between containers
docker exec godot-server ping claude-agent
```

### Image Too Large
```bash
# Check image size
docker images | grep lazy-bird

# Reduce size by:
# 1. Multi-stage builds
# 2. Remove unnecessary packages
# 3. Clean apt cache
# 4. Use Alpine base (advanced)

# Analyze layers
docker history lazy-bird/claude-agent:latest
```

## Performance Optimization

### 1. Use Build Cache
```bash
docker-compose build --parallel
```

### 2. Pre-pull Base Images
```bash
docker pull ubuntu:22.04
```

### 3. Use Docker BuildKit
```bash
export DOCKER_BUILDKIT=1
docker-compose build
```

### 4. Optimize Layer Order
Place frequently changing commands later in Dockerfile

## Cleanup

### Remove Stopped Containers
```bash
docker container prune
```

### Remove Unused Images
```bash
docker image prune -a
```

### Remove All Lazy_Bird Resources
```bash
docker-compose down -v
docker rmi lazy-bird/claude-agent:latest
docker rmi lazy-bird/godot-server:latest
docker volume rm lazy-bird-test-artifacts
```

## Production Deployment

### Using Docker Swarm (Optional)
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml lazy-bird

# Scale agents
docker service scale lazy-bird_claude-agent=3
```

### Using Kubernetes (Advanced)
See separate k8s/ directory for Kubernetes manifests (future enhancement).

## Monitoring

### View Resource Usage
```bash
docker stats
```

### View Logs
```bash
# Real-time logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100 godot-server
```

### Export Metrics
Configure Prometheus exporter (future enhancement):
```bash
docker run -d \
  --name cadvisor \
  --volume=/:/rootfs:ro \
  --volume=/var/run:/var/run:ro \
  --volume=/sys:/sys:ro \
  --volume=/var/lib/docker/:/var/lib/docker:ro \
  --publish=8080:8080 \
  google/cadvisor:latest
```

## Integration with Systemd

### Start on Boot
```bash
# Create systemd service
sudo tee /etc/systemd/system/lazy-bird-docker.service <<EOF
[Unit]
Description=Lazy_Bird Docker Services
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/lazy_birtd/docker
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
ExecReload=/usr/bin/docker-compose restart

[Install]
WantedBy=multi-user.target
EOF

# Enable service
sudo systemctl enable lazy-bird-docker
sudo systemctl start lazy-bird-docker
```

## License

MIT License - See LICENSE file in project root
