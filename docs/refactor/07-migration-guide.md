# Migration Guide - Lazy-Bird v1.1 to v2.0

**Status:** ✅ **IMPLEMENTED** (v2.0 Complete - 2026-01-03)

## Overview

This guide helps you migrate from Lazy-Bird v1.1 (Django-integrated) to v2.0 (microservice architecture).

**Migration Approach**: Blue-Green Deployment
- v1.1 (blue) continues running
- v2.0 (green) deployed in parallel
- Gradual traffic shift
- Rollback capability maintained

**Estimated Downtime**: Zero (seamless migration)

## Prerequisites

Before migrating, ensure:

- [ ] v2.0 infrastructure is ready (PostgreSQL, Redis, Docker/Kubernetes)
- [ ] Backup of v1.1 database completed
- [ ] API keys generated for v2.0
- [ ] Webhooks configured
- [ ] Team trained on new architecture

## Migration Checklist

### Phase 1: Preparation (Before Migration)

#### 1. Backup Current System

```bash
# Backup v1.1 database
pg_dump plane_db > backups/plane_v1.1_$(date +%Y%m%d).sql

# Export task history
python manage.py dumpdata lazy_bird > backups/lazy_bird_data.json

# Backup configuration
cp -r ~/.config/lazy_bird backups/config_v1.1/
```

#### 2. Deploy v2.0 Infrastructure

```bash
# Clone v2.0 repository
git clone https://github.com/yusyus/lazy-bird.git lazy-bird-v2
cd lazy-bird-v2
git checkout v2.0.0

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start services
docker-compose up -d

# Verify health
curl http://localhost:8000/health
```

#### 3. Migrate Data

**Script**: `scripts/migrate_v1_to_v2.py`

```python
"""Migrate data from v1.1 to v2.0"""
import asyncio
from django.core.management.base import BaseCommand
from plane.lazy_bird.models import (
    AutomationConfig as V1Config,
    TaskRun as V1TaskRun,
    ClaudeAccount as V1Account,
)
from lazy_bird_client import LazyBirdClient

class Command(BaseCommand):
    help = 'Migrate Lazy-Bird v1.1 data to v2.0'

    def handle(self, *args, **options):
        asyncio.run(self.migrate())

    async def migrate(self):
        client = LazyBirdClient(
            api_url=settings.LAZY_BIRD_V2_API_URL,
            api_key=settings.LAZY_BIRD_V2_API_KEY
        )

        # 1. Migrate Claude Accounts
        self.stdout.write("Migrating Claude accounts...")
        v1_accounts = V1Account.objects.all()
        for account in v1_accounts:
            v2_account = await client.accounts.create({
                "name": account.name,
                "account_type": account.account_type,
                "api_key": account.api_key,  # Encrypted
                "model": account.model or "claude-sonnet-4-5"
            })
            # Store mapping
            AccountMapping.objects.create(
                v1_id=account.id,
                v2_id=v2_account["id"]
            )

        # 2. Migrate Projects
        self.stdout.write("Migrating projects...")
        v1_configs = V1Config.objects.filter(enabled=True)
        for config in v1_configs:
            project = config.project

            # Get mapped account ID
            account_mapping = AccountMapping.objects.get(
                v1_id=config.claude_account_id
            )

            v2_project = await client.projects.create({
                "name": project.name,
                "slug": project.slug,
                "repo_url": f"https://github.com/{project.workspace.slug}/{project.slug}",
                "project_type": config.project_type,
                "automation_enabled": config.enabled,
                "ready_state_name": config.ready_state.name if config.ready_state else "Ready",
                "test_command": config.test_command,
                "claude_account_id": account_mapping.v2_id
            })

            # Store mapping
            ProjectMapping.objects.create(
                v1_project_id=project.id,
                v2_project_id=v2_project["id"]
            )

        # 3. Migrate Task History (last 30 days only)
        self.stdout.write("Migrating recent task runs...")
        cutoff_date = timezone.now() - timedelta(days=30)
        v1_tasks = V1TaskRun.objects.filter(
            created_at__gte=cutoff_date
        ).order_by('created_at')

        for task in v1_tasks:
            project_mapping = ProjectMapping.objects.get(
                v1_project_id=task.project_id
            )

            # Note: Can't create historical tasks via API
            # This is for reference/analytics only
            # Actual migration will use direct database insert
            pass

        self.stdout.write(self.style.SUCCESS('Migration completed!'))
```

**Run Migration**:
```bash
# From Plane directory
python manage.py migrate_lazy_bird_v1_to_v2

# Verify
curl http://localhost:8000/api/v1/projects | jq '.data | length'
```

---

### Phase 2: Parallel Operation (Week 1-2)

#### 1. Install Plane Integration Client

```bash
# Install v2.0 integration package
pip install plane-lazy-bird-integration

# Add to Plane settings
# plane/settings/common.py
INSTALLED_APPS = [
    ...
    'plane_lazy_bird',  # v2.0 integration
]

# Configure
LAZY_BIRD_API_URL = env('LAZY_BIRD_API_URL', 'http://localhost:8000')
LAZY_BIRD_API_KEY = env('LAZY_BIRD_API_KEY')
LAZY_BIRD_WEBHOOK_SECRET = env('LAZY_BIRD_WEBHOOK_SECRET')

# Run migrations
python manage.py migrate plane_lazy_bird

# Set up webhook
python manage.py lazy_bird_setup_webhook
```

#### 2. Configure Webhooks

```bash
# Register webhook endpoint in Lazy-Bird v2.0
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer $LAZY_BIRD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://plane.example.com/api/webhooks/lazy-bird",
    "secret": "whsec_...",
    "events": ["task.completed", "task.failed", "pr.created"]
  }'
```

#### 3. Test in Staging

```bash
# Create test issue in Plane
# Move to "Ready" state
# Verify:
# 1. Task queued in v2.0
# 2. Task executes
# 3. PR created
# 4. Webhook received
# 5. Issue updated in Plane
```

---

### Phase 3: Traffic Shift (Week 3)

#### Strategy: Feature Flag

**File**: `plane_lazy_bird/settings.py`

```python
# Feature flag to control which version handles new tasks
USE_LAZY_BIRD_V2 = env.bool('USE_LAZY_BIRD_V2', default=False)
V2_TRAFFIC_PERCENTAGE = env.int('LAZY_BIRD_V2_TRAFFIC', default=0)  # 0-100
```

**File**: `plane_lazy_bird/signals.py`

```python
import random
from django.conf import settings

@receiver(post_save, sender=Issue)
def on_issue_state_change(sender, instance, created, **kwargs):
    if created:
        return

    # Check if should use v2.0
    use_v2 = False

    if settings.USE_LAZY_BIRD_V2:
        use_v2 = True
    elif settings.V2_TRAFFIC_PERCENTAGE > 0:
        # Gradual rollout
        use_v2 = random.randint(1, 100) <= settings.V2_TRAFFIC_PERCENTAGE

    if use_v2:
        # v2.0 path
        handle_issue_state_change_v2(instance)
    else:
        # v1.1 path (existing code)
        handle_issue_state_change_v1(instance)
```

#### Gradual Rollout Schedule

**Week 3, Day 1**: 10% traffic
```bash
# Update environment
export LAZY_BIRD_V2_TRAFFIC=10
python manage.py restart
```

**Week 3, Day 2**: 25% traffic (if no issues)
```bash
export LAZY_BIRD_V2_TRAFFIC=25
```

**Week 3, Day 3**: 50% traffic
```bash
export LAZY_BIRD_V2_TRAFFIC=50
```

**Week 3, Day 4**: 75% traffic
```bash
export LAZY_BIRD_V2_TRAFFIC=75
```

**Week 3, Day 5**: 100% traffic
```bash
export USE_LAZY_BIRD_V2=true
export LAZY_BIRD_V2_TRAFFIC=100
```

#### Monitoring During Rollout

```bash
# Monitor error rates
watch -n 5 'curl -s http://localhost:8000/api/v1/status | jq'

# Monitor task success rate
psql lazy_bird -c "
  SELECT
    DATE(created_at) as date,
    COUNT(*) as total,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
    ROUND(100.0 * SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
  FROM task_runs
  WHERE created_at > NOW() - INTERVAL '7 days'
  GROUP BY DATE(created_at)
  ORDER BY date DESC;
"

# Check webhook delivery success
curl -s http://localhost:8000/api/v1/webhooks | jq '.data[] | {url, failure_count}'
```

#### Rollback Procedure

If issues arise:

```bash
# Immediate rollback
export USE_LAZY_BIRD_V2=false
export LAZY_BIRD_V2_TRAFFIC=0
python manage.py restart

# Or via environment variable file
echo "USE_LAZY_BIRD_V2=false" >> .env
echo "LAZY_BIRD_V2_TRAFFIC=0" >> .env
sudo systemctl restart plane
```

---

### Phase 4: Full Migration (Week 4)

#### 1. Switch to 100% v2.0

```bash
# Update production environment
export USE_LAZY_BIRD_V2=true

# Restart services
sudo systemctl restart plane
sudo systemctl restart lazy-bird-api
sudo systemctl restart lazy-bird-worker
```

#### 2. Deprecate v1.1 Code

```bash
# Mark v1.1 code as deprecated
# plane/lazy_bird/__init__.py
import warnings
warnings.warn(
    "plane.lazy_bird v1.1 is deprecated. Use plane_lazy_bird (v2.0 integration) instead.",
    DeprecationWarning
)
```

#### 3. Update Documentation

- Update README with v2.0 instructions
- Mark v1.1 docs as deprecated
- Link to migration guide

---

### Phase 5: Cleanup (Week 6)

After 30 days of stable v2.0 operation:

#### 1. Remove v1.1 Code

```bash
# Create backup branch
git checkout -b archive/v1.1
git push origin archive/v1.1

# Remove v1.1 integration code
git checkout main
git rm -r apps/api/plane/lazy_bird/
git commit -m "Remove deprecated v1.1 Lazy-Bird integration"
```

#### 2. Clean Database

```bash
# Archive v1.1 tables
psql plane_db <<EOF
  ALTER TABLE lazy_bird_taskrun RENAME TO _archived_v1_taskrun;
  ALTER TABLE lazy_bird_config RENAME TO _archived_v1_config;
EOF

# Drop after confirmation (wait 90 days)
# DROP TABLE _archived_v1_taskrun;
```

#### 3. Update Dependencies

```bash
# Remove v1.1 dependencies
pip uninstall django-celery-beat  # If only used by v1.1

# Update requirements
pip freeze > requirements.txt
```

---

## Troubleshooting

### Issue: Webhooks Not Received

**Symptoms**: Tasks complete but Plane issues not updated

**Solution**:
```bash
# 1. Verify webhook is registered
curl http://localhost:8000/api/v1/webhooks | jq

# 2. Check webhook logs
curl http://localhost:8000/api/v1/webhooks/wh_xxx/deliveries | jq

# 3. Test webhook manually
curl -X POST http://localhost:8000/api/v1/webhooks/wh_xxx/test

# 4. Check signature verification
# In Plane webhook handler, add debug logging
logger.debug(f"Received signature: {request.headers.get('X-Lazy-Bird-Signature')}")
logger.debug(f"Computed signature: {expected_sig}")
```

### Issue: Tasks Not Queuing

**Symptoms**: Moving issue to "Ready" state doesn't queue task

**Solution**:
```bash
# 1. Check project exists in v2.0
curl http://localhost:8000/api/v1/projects | jq '.data[] | {id, name, automation_enabled}'

# 2. Verify project mapping
python manage.py shell
>>> from plane_lazy_bird.models import AutomationConfig
>>> AutomationConfig.objects.filter(enabled=True)

# 3. Check API key permissions
curl -H "Authorization: Bearer $API_KEY" http://localhost:8000/api/v1/status

# 4. Check signal is firing
# Add debug logging to signals.py
logger.info(f"Issue {instance.id} state changed to {instance.state.name}")
```

### Issue: Performance Degradation

**Symptoms**: Slower task execution in v2.0

**Solution**:
```bash
# 1. Check resource usage
docker stats

# 2. Scale workers
docker-compose up -d --scale worker=3

# 3. Check database connections
psql lazy_bird -c "SELECT count(*) FROM pg_stat_activity;"

# 4. Check Celery queue depth
celery -A lazy_bird.tasks inspect active
celery -A lazy_bird.tasks inspect reserved
```

### Issue: Authentication Errors

**Symptoms**: 401 Unauthorized responses

**Solution**:
```bash
# 1. Verify API key format
echo $LAZY_BIRD_API_KEY | cut -c1-8
# Should output: lb_live_

# 2. Check API key in database
psql lazy_bird -c "SELECT key_prefix, is_active FROM api_keys;"

# 3. Test authentication
curl -v -H "Authorization: Bearer $LAZY_BIRD_API_KEY" \
  http://localhost:8000/api/v1/projects

# 4. Regenerate API key if needed
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer $ADMIN_API_KEY" \
  -d '{"name": "Plane Integration", "scopes": ["read", "write"]}'
```

---

## Data Verification

After migration, verify data integrity:

```bash
# Compare project counts
echo "v1.1 projects:"
psql plane_db -c "SELECT COUNT(*) FROM lazy_bird_config WHERE enabled = true;"

echo "v2.0 projects:"
psql lazy_bird -c "SELECT COUNT(*) FROM projects WHERE automation_enabled = true;"

# Compare task counts (last 30 days)
echo "v1.1 tasks:"
psql plane_db -c "SELECT COUNT(*) FROM lazy_bird_taskrun WHERE created_at > NOW() - INTERVAL '30 days';"

echo "v2.0 tasks:"
psql lazy_bird -c "SELECT COUNT(*) FROM task_runs WHERE created_at > NOW() - INTERVAL '30 days';"

# Check for missing data
python scripts/verify_migration.py
```

---

## Post-Migration Checklist

- [ ] All projects migrated and automation enabled
- [ ] Webhooks configured and delivering successfully
- [ ] Task execution working end-to-end
- [ ] PR creation successful
- [ ] Issue updates working in Plane
- [ ] Real-time logs streaming correctly
- [ ] No increase in error rates
- [ ] Performance metrics acceptable
- [ ] v1.1 code removed or deprecated
- [ ] Team trained on new architecture
- [ ] Documentation updated
- [ ] Monitoring dashboards configured

---

## Support

For migration assistance:
- GitHub Issues: https://github.com/yusyus/lazy-bird/issues
- Discussions: https://github.com/yusyus/lazy-bird/discussions
- Email: support@lazy-bird.dev

---

**Next**: [Testing Strategy](08-testing-strategy.md)
