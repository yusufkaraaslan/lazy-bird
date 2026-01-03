# Security Baseline

**Applies to:** ALL lazy-bird repositories
**Related repos:**
- ✅ lazy-bird (core engine)
- ✅ lazy-bird-ui (web interface)
- ✅ plane-lazy-bird-integration (Plane integration)
**Status:** ✅ Critical - MUST follow for all implementations

## Overview

Lazy_Birtd automates game development by running Claude Code with access to your codebase, git repository, and potentially destructive operations. **Security must be a top priority.**

This document establishes the security baseline for all phases of the system.

## Threat Model

### Assets to Protect

1. **Source Code** - Your game project
2. **Git History** - Commit integrity
3. **API Tokens** - GitHub/GitLab, Claude API keys
4. **Secrets** - Credentials, keys, passwords in code
5. **System Access** - Prevent unauthorized access to automation
6. **Personal Data** - Any user data in project

### Threat Actors

1. **Malicious Actor** - Gains access to automation system
2. **Compromised Dependency** - Malicious code in dependencies
3. **Claude Code Error** - Accidental destructive operation
4. **API Token Leak** - Tokens committed to git or exposed

### Attack Vectors

1. Network access to exposed services (Godot server, dashboard)
2. Compromised API tokens
3. Code injection via malicious issue descriptions
4. File system access beyond project scope
5. Privilege escalation
6. Supply chain attacks (Docker images, scripts)

## Security Principles

1. **Least Privilege** - Grant minimum necessary permissions
2. **Defense in Depth** - Multiple layers of security
3. **Fail Secure** - Default to safe state on errors
4. **Audit Everything** - Log all security-relevant events
5. **Secrets Never in Git** - No credentials in version control
6. **Isolation** - Contain failures and breaches
7. **Regular Updates** - Keep all components patched

## Secret Management

### What are Secrets?

- API tokens (GitHub, GitLab, Claude)
- SSH keys
- VPN private keys
- Webhook URLs
- Database passwords
- Encryption keys
- Any credential or sensitive data

### Storage Requirements

**❌ NEVER:**
- Commit secrets to git
- Store secrets in plain text in config files
- Pass secrets as command-line arguments (visible in ps)
- Log secrets
- Share secrets via unencrypted channels

**✅ ALWAYS:**
- Use dedicated secrets directory with restricted permissions
- Encrypt secrets at rest
- Load secrets from environment or secure files
- Rotate secrets regularly
- Use separate secrets for dev/prod

### Implementation

**Directory Structure:**
```bash
~/.config/lazy_birtd/
├── config.yml          # Public configuration
└── secrets/            # chmod 700 (owner only)
    ├── api_token       # chmod 600
    ├── claude_key      # chmod 600
    ├── ssh_key         # chmod 600
    └── vpn_key         # chmod 600
```

**Setup Script:**
```bash
#!/bin/bash
# scripts/setup-secrets.sh

SECRETS_DIR=~/.config/lazy_birtd/secrets

# Create secrets directory
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

# Store GitHub/GitLab token
read -s -p "Enter GitHub/GitLab API token: " TOKEN
echo "$TOKEN" > "$SECRETS_DIR/api_token"
chmod 600 "$SECRETS_DIR/api_token"
echo "✓ API token saved"

# Store Claude API key
read -s -p "Enter Claude API key: " CLAUDE_KEY
echo "$CLAUDE_KEY" > "$SECRETS_DIR/claude_key"
chmod 600 "$SECRETS_DIR/claude_key"
echo "✓ Claude API key saved"

# Verify permissions
echo ""
echo "Verifying permissions..."
ls -la "$SECRETS_DIR"
```

**Loading Secrets:**
```python
# scripts/load_secrets.py
from pathlib import Path
import os

def load_secret(name):
    """Load secret from secure storage"""
    secrets_dir = Path.home() / '.config/lazy_birtd/secrets'
    secret_file = secrets_dir / name

    if not secret_file.exists():
        raise FileNotFoundError(f"Secret '{name}' not found")

    # Verify permissions
    mode = secret_file.stat().st_mode & 0o777
    if mode != 0o600:
        raise PermissionError(f"Secret '{name}' has insecure permissions: {oct(mode)}")

    return secret_file.read_text().strip()

# Usage
api_token = load_secret('api_token')
claude_key = load_secret('claude_key')
```

**Environment Variables (Alternative):**
```bash
# ~/.bashrc or systemd service file
export LAZY_BIRTD_API_TOKEN=$(cat ~/.config/lazy_birtd/secrets/api_token)
export LAZY_BIRTD_CLAUDE_KEY=$(cat ~/.config/lazy_birtd/secrets/claude_key)
```

### .gitignore Configuration

**Critical:**
```gitignore
# Lazy_Birtd - DO NOT COMMIT
.env
.env.*
*_secret*
*_key*
*.pem
*.key
secrets/
api_token*
claude_key*

# Config with sensitive data
config.yml  # If it contains secrets; otherwise allow it

# Logs may contain tokens
logs/
*.log

# Backups may contain secrets
backup/
*.backup
*.bak
```

### Secret Rotation

**Schedule:**
- API tokens: Every 90 days
- SSH keys: Every 180 days
- VPN keys: Every 180 days
- After any suspected compromise: Immediately

**Rotation Script:**
```bash
#!/bin/bash
# scripts/rotate-secrets.sh

echo "🔄 Secret Rotation"
echo ""

# Check last rotation date
LAST_ROTATION=$(cat ~/.config/lazy_birtd/secrets/.last_rotation 2>/dev/null || echo "never")
echo "Last rotation: $LAST_ROTATION"

# Rotate API token
echo ""
echo "1. Generate new token at:"
echo "   GitHub: https://github.com/settings/tokens"
echo "   GitLab: https://gitlab.com/-/profile/personal_access_tokens"

read -s -p "Enter new token: " NEW_TOKEN

# Backup old token (encrypted)
OLD_TOKEN=$(cat ~/.config/lazy_birtd/secrets/api_token)
echo "$OLD_TOKEN" | gpg --encrypt > ~/.config/lazy_birtd/secrets/api_token.old.gpg

# Save new token
echo "$NEW_TOKEN" > ~/.config/lazy_birtd/secrets/api_token"
chmod 600 ~/.config/lazy_birtd/secrets/api_token

# Update last rotation date
date -I > ~/.config/lazy_birtd/secrets/.last_rotation

echo "✓ Token rotated"
echo ""
echo "⚠️  Remember to:"
echo "  1. Revoke old token in GitHub/GitLab"
echo "  2. Test new token works"
echo "  3. Update any external integrations"
```

## Service Authentication

### Godot Server

**Problem:** HTTP API exposed on port 5000

**Solutions:**

**Option 1: API Key Authentication**
```python
# godot-server.py
from functools import wraps
from flask import request, jsonify

API_KEY = load_secret('godot_api_key')

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-API-Key')
        if key != API_KEY:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/test/submit', methods=['POST'])
@require_api_key
def submit_test():
    # ... implementation
```

**Client Usage:**
```python
api_key = load_secret('godot_api_key')
response = requests.post(
    'http://localhost:5000/test/submit',
    headers={'X-API-Key': api_key},
    json=test_data
)
```

**Option 2: Network Isolation**
```bash
# Only bind to localhost (not 0.0.0.0)
app.run(host='127.0.0.1', port=5000)

# Or use firewall to restrict access
sudo ufw allow from 127.0.0.1 to any port 5000
sudo ufw deny 5000
```

**Option 3: mTLS (Mutual TLS)**
```python
# For production, use SSL with client certificates
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('server.crt', 'server.key')
context.load_verify_locations('ca.crt')
context.verify_mode = ssl.CERT_REQUIRED

app.run(ssl_context=context)
```

### Dashboard (Phase 3)

**Problem:** Web dashboard exposes system status

**Solutions:**

**Basic HTTP Auth:**
```python
from flask_httpauth import HTTPBasicAuth

auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    stored_hash = load_secret('dashboard_password_hash')
    return check_password_hash(stored_hash, password)

@app.route('/')
@auth.login_required
def dashboard():
    return render_template('dashboard.html')
```

**OAuth2 (Advanced):**
```python
# Use GitHub/GitLab OAuth for authentication
from flask_dance.contrib.github import make_github_blueprint, github

github_bp = make_github_blueprint(client_id='...', client_secret='...')
app.register_blueprint(github_bp, url_prefix='/login')

@app.route('/')
def dashboard():
    if not github.authorized:
        return redirect(url_for('github.login'))

    resp = github.get('/user')
    # Verify user is authorized
    if resp.json()['login'] not in ALLOWED_USERS:
        return "Unauthorized", 403

    return render_template('dashboard.html')
```

### SSH Access

**Harden SSH for remote access:**

```bash
# /etc/ssh/sshd_config
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AllowUsers lazybirtd
MaxAuthTries 3
LoginGraceTime 30
```

**Key-based Auth Only:**
```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "lazy_birtd_access"

# Add public key to server
ssh-copy-id -i ~/.ssh/lazy_birtd.pub user@server

# Connect
ssh -i ~/.ssh/lazy_birtd user@server
```

## Network Security

### Firewall Configuration

**ufw (Ubuntu/Debian):**
```bash
# Default deny
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (if needed)
sudo ufw allow 22/tcp

# Allow VPN (Phase 3)
sudo ufw allow 51820/udp

# Godot Server - localhost only (no rule needed)
# Dashboard - localhost only or VPN only
sudo ufw allow from 10.0.0.0/24 to any port 5000

# Enable firewall
sudo ufw enable
```

**firewalld (Fedora/RHEL):**
```bash
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-port=51820/udp
sudo firewall-cmd --reload
```

### VPN Security (Phase 3)

**WireGuard Best Practices:**

```bash
# Generate keys securely
umask 077
wg genkey | tee private_key | wg pubkey > public_key

# Server config
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = <server_private_key>
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
PublicKey = <client_public_key>
AllowedIPs = 10.0.0.2/32

# Restrict access to dashboard via VPN only
sudo ufw allow from 10.0.0.0/24 to any port 5000
sudo ufw deny 5000
```

**Key Management:**
```bash
# Store VPN keys securely
cp wg0.conf ~/.config/lazy_birtd/secrets/vpn_server.conf
chmod 600 ~/.config/lazy_birtd/secrets/vpn_server.conf

# Never commit WireGuard configs
echo "*.conf" >> .gitignore
```

## Docker Security

### Image Security

**Use Official Images:**
```dockerfile
# Good - official base
FROM ubuntu:22.04

# Bad - unknown source
FROM randomuser/ubuntu
```

**Pin Versions:**
```dockerfile
# Good - specific version
FROM ubuntu:22.04

# Bad - moving target
FROM ubuntu:latest
```

**Scan Images:**
```bash
# Install trivy
sudo pacman -S trivy

# Scan image for vulnerabilities
trivy image lazy-birtd/claude-agent:latest

# Fail build if critical vulns found
trivy image --severity CRITICAL,HIGH --exit-code 1 lazy-birtd/claude-agent:latest
```

### Container Isolation

**Run as Non-Root:**
```dockerfile
# Create non-root user
RUN useradd -m -u 1000 lazybirtd

# Switch to non-root
USER lazybirtd

# Run app
CMD ["python3", "agent.py"]
```

**Resource Limits:**
```yaml
# docker-compose.yml
services:
  godot-server:
    mem_limit: 4g
    cpus: 2
    read_only: true  # Filesystem read-only except volumes
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only if needed
```

**Network Isolation:**
```yaml
# docker-compose.yml
networks:
  internal:
    internal: true  # No internet access
  external:
    # Has internet

services:
  godot-server:
    networks:
      - internal  # Isolated

  issue-watcher:
    networks:
      - external  # Needs API access
```

## Input Validation

### Issue Body Sanitization

**Problem:** Malicious code in issue descriptions could be executed

**Solution: Parse and Sanitize**
```python
import re
import bleach

def sanitize_issue_body(body):
    """Clean issue body of potentially dangerous content"""

    # Remove script tags
    body = re.sub(r'<script.*?</script>', '', body, flags=re.DOTALL)

    # Remove dangerous markdown
    body = re.sub(r'!\[.*?\]\(javascript:.*?\)', '', body)

    # Sanitize HTML if any
    body = bleach.clean(body, tags=['p', 'code', 'pre', 'ul', 'ol', 'li'])

    # Limit length
    max_length = 50000
    if len(body) > max_length:
        body = body[:max_length] + "\n[Truncated]"

    return body

def validate_task(task):
    """Validate task structure before processing"""

    # Required fields
    if not task.get('title'):
        raise ValueError("Task must have title")

    # Validate complexity
    valid_complexity = ['simple', 'medium', 'complex']
    if task.get('complexity') not in valid_complexity:
        task['complexity'] = 'medium'  # Default

    # Sanitize body
    task['body'] = sanitize_issue_body(task.get('body', ''))

    return task
```

### Path Traversal Prevention

**Problem:** Malicious paths could access files outside project

**Solution: Validate Paths**
```python
from pathlib import Path

def validate_project_path(path, base_path):
    """Ensure path is within base_path"""

    path = Path(path).resolve()
    base = Path(base_path).resolve()

    if not str(path).startswith(str(base)):
        raise ValueError(f"Path {path} outside project {base}")

    return path

# Usage
project_path = validate_project_path(
    user_input_path,
    '/var/lib/lazy_birtd/projects'
)
```

## Audit Logging

### What to Log

**Security Events:**
- Authentication attempts (success/failure)
- API token usage
- Secret access
- File modifications outside project
- Network connections
- Privilege escalations
- Configuration changes

**Operational Events:**
- Task submissions
- Test executions
- PR creations
- Retries and failures

### Log Format

```python
import logging
import json
from datetime import datetime

class SecurityLogger:
    def __init__(self):
        self.logger = logging.getLogger('security')
        handler = logging.FileHandler('/var/log/lazy_birtd/security.log')
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_event(self, event_type, details, severity='INFO'):
        """Log security event in structured format"""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': event_type,
            'severity': severity,
            'details': details,
            'user': os.getenv('USER'),
            'pid': os.getpid()
        }
        self.logger.info(json.dumps(event))

# Usage
security_log = SecurityLogger()

# Log API token access
security_log.log_event('secret_access', {
    'secret': 'api_token',
    'purpose': 'github_api_call'
})

# Log authentication failure
security_log.log_event('auth_failure', {
    'service': 'godot_server',
    'ip': request.remote_addr
}, severity='WARNING')

# Log privilege escalation attempt
security_log.log_event('privilege_escalation', {
    'command': 'sudo',
    'denied': True
}, severity='CRITICAL')
```

### Log Retention

```bash
# logrotate config: /etc/logrotate.d/lazy_birtd
/var/log/lazy_birtd/*.log {
    daily
    rotate 90
    compress
    delaycompress
    notifempty
    create 640 lazybirtd lazybirtd
    sharedscripts
    postrotate
        systemctl reload lazy_birtd-* > /dev/null
    endscript
}
```

## Security Checklist

### Pre-Deployment

- [ ] All secrets stored in `~/.config/lazy_birtd/secrets/` with chmod 600
- [ ] No secrets in git history
- [ ] `.gitignore` configured for secrets
- [ ] Firewall configured (ufw/firewalld)
- [ ] Services bound to localhost or VPN only
- [ ] API authentication enabled
- [ ] Docker images scanned for vulnerabilities
- [ ] Containers run as non-root
- [ ] Audit logging enabled
- [ ] SSH hardened (key-only, no root)
- [ ] Regular backup strategy in place

### Post-Deployment

- [ ] Monitor security logs daily
- [ ] Rotate secrets every 90 days
- [ ] Update dependencies monthly
- [ ] Review access logs weekly
- [ ] Test backup restoration quarterly
- [ ] Security audit annually

### Incident Response

**If Token Compromised:**
1. Immediately revoke token in GitHub/GitLab
2. Generate new token
3. Update secret file
4. Review git history for any malicious commits
5. Review access logs for suspicious activity
6. Notify affected parties if data exposed

**If System Compromised:**
1. Disconnect from network
2. Preserve logs and evidence
3. Analyze extent of compromise
4. Rebuild from clean state
5. Rotate all secrets
6. Review and patch vulnerability
7. Document incident and lessons learned

## Future Enhancements

### Planned Security Features

1. **Secret Encryption at Rest** - Use GPG or age to encrypt secrets
2. **Hardware Security Module (HSM)** - Store keys in hardware
3. **Intrusion Detection** - Automated anomaly detection
4. **2FA for Dashboard** - Multi-factor authentication
5. **SOC 2 Compliance** - For commercial use
6. **Penetration Testing** - Annual security assessment

## Conclusion

Security is not optional for automated systems with code access. This baseline provides:

- ✅ Secret management strategy
- ✅ Service authentication
- ✅ Network isolation
- ✅ Docker security
- ✅ Input validation
- ✅ Audit logging
- ✅ Incident response plan

Follow these guidelines to ensure your automation system is secure and trustworthy.

**Remember:** Security is a process, not a product. Stay vigilant, keep systems updated, and review security regularly.
