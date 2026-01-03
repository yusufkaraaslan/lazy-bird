# Test Retry Logic Specification

**Applies to:** lazy-bird core engine (all versions)
**Related repos:** lazy-bird (core) - NOT lazy-bird-ui or plane-lazy-bird-integration
**Status:** ✅ **IMPLEMENTED** in v2.0

## Overview

When automated tests fail, the system should attempt to fix the issues and retry - but not indefinitely. This document specifies the retry behavior, limits, and escalation strategies.

## Core Principles

1. **Fail fast on unrecoverable errors** - Don't retry if it won't help
2. **Learn from failures** - Pass error context to Claude for fixing
3. **Limit retry attempts** - Prevent infinite loops and cost explosion
4. **Escalate intelligently** - Know when to involve humans
5. **Preserve debugging context** - Save all logs and state

## Retry Limits

### Default Limits

| Scenario | Max Retries | Total Attempts |
|----------|-------------|----------------|
| Test failures | 3 | 4 (1 initial + 3 retries) |
| Godot crashes | 2 | 3 |
| Compilation errors | 2 | 3 |
| Timeout | 1 | 2 |
| API errors | 5 | 6 (with exponential backoff) |
| Git conflicts | 1 | 2 (then escalate) |

### Configurable Per-Task

Users can override retry limits in issue body:

```markdown
## Retry Configuration
max_retries: 5
timeout_seconds: 600
allow_retry_on: [test_failure, compilation_error]
```

## Retry Decision Tree

```
Test Run
   ↓
[Pass?] → Yes → Create PR → Done ✓
   ↓
  No
   ↓
[Retries Remaining?] → No → Fail Task, Notify User ✗
   ↓
  Yes
   ↓
[Error Type?]
   ├─ Test Failure → Parse errors → Give to Claude → Retry
   ├─ Compilation Error → Parse errors → Give to Claude → Retry
   ├─ Godot Crash → Check logs → Restart Godot → Retry
   ├─ Timeout → Increase timeout → Retry
   ├─ Git Conflict → Rebase/Merge → Retry
   └─ Unknown → Save state → Escalate to User ✗
```

## Error Classification

### Retriable Errors

**Test Failures:**
```
❌ test_player_health: Expected 100, got 0
❌ test_take_damage: Signal not emitted
```
**Action:** Parse error, pass to Claude with context, retry

**Compilation/Syntax Errors:**
```
Parse Error: Expected ')' on line 42
Invalid get index 'helth' (on base: 'Player')
```
**Action:** Claude can fix typos and syntax, retry

**Godot Crashes (recoverable):**
```
Godot crashed with signal 11 (SIGSEGV)
Stack trace: [...]
```
**Action:** Restart Godot, retry (may be transient)

**Timeouts:**
```
Test exceeded 300s timeout
```
**Action:** Increase timeout, retry once

### Non-Retriable Errors

**Missing Dependencies:**
```
Cannot find addon 'ExamplePlugin'
Required export template missing
```
**Action:** Fail immediately, notify user

**Permission Errors:**
```
Permission denied: /etc/godot/config
Cannot write to read-only filesystem
```
**Action:** Fail immediately, check setup

**Git Conflicts (after attempt):**
```
CONFLICT (content): Merge conflict in player.gd
```
**Action:** One rebase attempt, then escalate

**API Rate Limits:**
```
HTTP 429: Too Many Requests
Retry-After: 3600
```
**Action:** Don't retry immediately, queue for later

**Resource Exhaustion:**
```
Out of memory
Disk full
```
**Action:** Fail immediately, alert admin

## Retry Implementation

### Test Failure Retry

```python
def execute_task_with_retry(task):
    max_retries = task.get('max_retries', 3)
    attempt = 0

    while attempt <= max_retries:
        attempt += 1
        print(f"Attempt {attempt}/{max_retries + 1}")

        # Run agent on task
        result = run_agent(task)

        if result.success:
            # Tests passed!
            return create_pr(task, result)

        # Tests failed - decide if we should retry
        if not should_retry(result.error, attempt, max_retries):
            return fail_task(task, result, attempts=attempt)

        # Prepare retry with error context
        task_with_context = add_error_context(task, result)

        # Wait before retry (exponential backoff)
        wait_time = min(60 * (2 ** (attempt - 1)), 300)  # Max 5 min
        time.sleep(wait_time)

    # Exhausted all retries
    return fail_task(task, result, attempts=attempt)

def should_retry(error, attempt, max_retries):
    """Decide if error is retriable"""
    if attempt > max_retries:
        return False

    # Check error type
    if error.type in ['test_failure', 'compilation_error']:
        return True
    elif error.type == 'godot_crash':
        return attempt <= 2  # Only retry crashes twice
    elif error.type == 'timeout':
        return attempt == 1  # Only retry timeout once
    elif error.type in ['permission_error', 'missing_dependency']:
        return False  # Never retry these
    else:
        return True  # Default: retry unknown errors

def add_error_context(task, result):
    """Add error information to task for Claude to fix"""
    error_context = f"""

## Previous Attempt Failed

**Error Type:** {result.error.type}

**Error Message:**
```
{result.error.message}
```

**Failed Tests:**
{format_failed_tests(result.test_results)}

**What Went Wrong:**
{analyze_failure(result)}

**Please fix the issues above and try again.**
"""

    task['description'] = task['description'] + error_context
    task['is_retry'] = True
    task['retry_attempt'] = task.get('retry_attempt', 0) + 1

    return task

def format_failed_tests(test_results):
    """Format failed tests for Claude"""
    failed = [t for t in test_results if t.status == 'failed']

    output = []
    for test in failed:
        output.append(f"- **{test.name}**")
        output.append(f"  Expected: {test.expected}")
        output.append(f"  Got: {test.actual}")
        output.append(f"  Location: {test.file}:{test.line}")
        output.append("")

    return "\n".join(output)

def analyze_failure(result):
    """Provide hints about what might be wrong"""
    hints = []

    # Check for common patterns
    if 'null' in str(result.error).lower():
        hints.append("- Looks like a null reference - check object initialization")

    if 'signal' in str(result.error).lower():
        hints.append("- Signal not emitted/connected - verify signal declaration and emission")

    if 'expected' in str(result.error).lower() and 'got' in str(result.error).lower():
        hints.append("- Value mismatch - check your calculations and logic")

    if 'timeout' in str(result.error).lower():
        hints.append("- Test timed out - might be infinite loop or waiting for event that never happens")

    if not hints:
        hints.append("- Review the error message above and the test expectations")

    return "\n".join(hints)
```

### Godot Server Integration

```python
def run_tests_with_retry(project_path, test_suite, max_retries=3):
    """Run tests through Godot Server with retry"""
    godot_client = GodotClient()
    attempt = 0

    while attempt <= max_retries:
        attempt += 1

        try:
            # Submit test job
            job_id = godot_client.submit_test(
                project_path=project_path,
                test_suite=test_suite,
                timeout=300
            )

            # Wait for result
            result = godot_client.wait_for_result(job_id)

            if result['result'] == 'passed':
                return {'success': True, 'result': result}
            else:
                # Tests failed
                error = {
                    'type': 'test_failure',
                    'message': f"{result['summary']['failed']} tests failed",
                    'details': result
                }

                if attempt > max_retries:
                    return {'success': False, 'error': error, 'result': result}

                print(f"⚠️  Tests failed (attempt {attempt}/{max_retries + 1})")
                print(f"   Failed: {result['summary']['failed']}")
                print(f"   Retrying with error context...")

        except GodotCrashException as e:
            # Godot crashed
            error = {
                'type': 'godot_crash',
                'message': str(e)
            }

            if attempt > 2:  # Only retry crashes twice
                return {'success': False, 'error': error}

            print(f"⚠️  Godot crashed (attempt {attempt}/3)")
            print(f"   Restarting Godot server...")
            restart_godot_server()
            time.sleep(10)  # Wait for server to stabilize

        except TimeoutException as e:
            # Test timed out
            error = {
                'type': 'timeout',
                'message': f"Test exceeded timeout"
            }

            if attempt > 1:  # Only retry timeout once
                return {'success': False, 'error': error}

            print(f"⚠️  Test timed out (attempt {attempt}/2)")
            # Increase timeout for retry
            timeout = 600  # 10 minutes

    return {'success': False, 'error': error}
```

## Retry Notifications

### After Each Retry

**Console Output:**
```
🔄 Retry attempt 2/4 for task #42
   Reason: 3 tests failed
   Previous error: Expected 100, got 0
   Giving Claude error context to fix...
```

**Issue Comment (optional):**
```markdown
🔄 **Retry Attempt 2/4**

Tests failed in previous attempt. Retrying with error context.

**Failed Tests:**
- test_player_health: Expected 100, got 0
- test_take_damage: Signal not emitted

[View full test output](link-to-logs)
```

### On Retry Success

**Console Output:**
```
✅ Task #42 succeeded on attempt 3/4
   Tests passing after fixes
   Creating PR...
```

**Issue Comment:**
```markdown
✅ **Task Complete** (succeeded on retry attempt 3)

All tests now passing after fixing issues from previous attempts.

**Pull Request:** #123
```

**ntfy.sh:**
```bash
curl -d "✅ Task #42 complete (retry 3/4) - PR created" \
  https://ntfy.sh/my-game-dev
```

### On Retry Exhaustion

**Console Output:**
```
❌ Task #42 failed after 4 attempts
   Max retries (3) exhausted
   Last error: 3 tests still failing
   Manual intervention required
```

**Issue Comment:**
```markdown
❌ **Task Failed** after 4 attempts

Unable to fix issues automatically. Manual intervention required.

**Attempts Summary:**
1. ❌ Initial: 5 tests failed
2. ❌ Retry 1: 4 tests failed (fixed 1)
3. ❌ Retry 2: 3 tests failed (fixed 1)
4. ❌ Retry 3: 3 tests failed (no improvement)

**Remaining Issues:**
- test_player_health: Expected 100, got 0
- test_take_damage: Signal not emitted
- test_heal: Null reference error

**Logs:** [View full output](link-to-logs)

**Next Steps:**
1. Review the errors above
2. Check if task description was clear enough
3. Update task with more specific instructions
4. Re-add `ready` label to retry from scratch
```

**ntfy.sh (high priority):**
```bash
curl -d "❌ Task #42 failed after 4 attempts - needs manual review" \
  -H "Priority: high" \
  https://ntfy.sh/my-game-dev
```

## Backoff Strategy

### Time Between Retries

```python
def calculate_backoff(attempt, base=60, max_wait=300):
    """Exponential backoff with jitter"""
    wait = min(base * (2 ** (attempt - 1)), max_wait)
    jitter = random.uniform(0, wait * 0.1)  # 10% jitter
    return wait + jitter

# Examples:
# Attempt 1: 60s + jitter = ~60-66s
# Attempt 2: 120s + jitter = ~120-132s
# Attempt 3: 240s + jitter = ~240-264s
# Attempt 4: 300s (capped) + jitter = ~300-330s
```

**Why Backoff?**
- Gives Claude "think time" between attempts
- Reduces API rate limit pressure
- Allows transient issues to resolve
- Prevents tight retry loops

## API Rate Limit Handling

### Claude API Retry

```python
def call_claude_with_retry(prompt, max_retries=5):
    """Call Claude API with exponential backoff on rate limits"""
    for attempt in range(max_retries + 1):
        try:
            return claude.complete(prompt)

        except RateLimitError as e:
            if attempt >= max_retries:
                raise

            # Extract retry-after if provided
            retry_after = e.retry_after or (60 * (2 ** attempt))

            print(f"⚠️  Rate limited. Waiting {retry_after}s...")
            time.sleep(retry_after)

        except APIError as e:
            if e.status_code >= 500:
                # Server error, retry with backoff
                if attempt >= max_retries:
                    raise

                wait = 30 * (2 ** attempt)
                print(f"⚠️  API error {e.status_code}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                # Client error (4xx), don't retry
                raise
```

## Cost Control

### Budget Limits

```yaml
# config.yml
cost_control:
  max_retries_per_task: 3
  max_cost_per_task_usd: 5.0
  daily_budget_usd: 50.0
  alert_at_percentage: 80
```

### Cost Tracking

```python
class CostTracker:
    def __init__(self):
        self.daily_cost = 0.0
        self.task_costs = {}

    def record_attempt(self, task_id, cost):
        """Record cost of an attempt"""
        self.daily_cost += cost
        self.task_costs[task_id] = self.task_costs.get(task_id, 0) + cost

    def can_retry(self, task_id, config):
        """Check if retry is within budget"""
        task_cost = self.task_costs.get(task_id, 0)

        # Check task budget
        if task_cost >= config['max_cost_per_task_usd']:
            print(f"⚠️  Task #{task_id} exceeded cost limit (${task_cost:.2f})")
            return False

        # Check daily budget
        if self.daily_cost >= config['daily_budget_usd']:
            print(f"⚠️  Daily budget exceeded (${self.daily_cost:.2f})")
            return False

        # Alert if approaching limit
        daily_pct = (self.daily_cost / config['daily_budget_usd']) * 100
        if daily_pct >= config['alert_at_percentage']:
            print(f"⚠️  Daily budget at {daily_pct:.0f}% (${self.daily_cost:.2f})")

        return True
```

## Retry Metrics

### Track Retry Patterns

```python
class RetryMetrics:
    """Track retry statistics for analysis"""

    def record_task_result(self, task_id, attempts, success):
        """Record task outcome"""
        metric = {
            'task_id': task_id,
            'attempts': attempts,
            'success': success,
            'timestamp': datetime.now(),
            'cost': calculate_cost(attempts)
        }
        self.save_metric(metric)

    def get_success_rate(self, days=7):
        """Calculate success rate including retries"""
        metrics = self.load_metrics(days)
        total = len(metrics)
        successful = sum(1 for m in metrics if m['success'])
        return (successful / total) * 100 if total > 0 else 0

    def get_average_attempts(self, days=7):
        """Average attempts needed for success"""
        metrics = self.load_metrics(days)
        successful = [m for m in metrics if m['success']]
        if not successful:
            return 0
        return sum(m['attempts'] for m in successful) / len(successful)

    def get_retry_reasons(self, days=7):
        """Most common reasons for retries"""
        # Returns dict of {reason: count}
        pass
```

### Weekly Report

```
📊 Retry Statistics (Last 7 Days)

Success Rate: 92.5% (37/40 tasks)
Average Attempts: 1.8 (for successful tasks)

Retry Breakdown:
  No retries needed: 24 (60%)
  1 retry: 8 (20%)
  2 retries: 5 (12.5%)
  3 retries (max): 0
  Failed after max retries: 3 (7.5%)

Common Retry Reasons:
  1. Test failures: 15 (68%)
  2. Compilation errors: 5 (23%)
  3. Godot crashes: 2 (9%)

Improvement Suggestions:
  - 3 tasks repeatedly failed on null references
    → Consider adding null checks to templates
  - Average 1.8 attempts suggests good first-try rate
    → Continue current task description format
```

## Best Practices

### For Users Writing Tasks

**Do:**
- ✅ Provide clear, specific steps
- ✅ Include expected file names and locations
- ✅ Specify test requirements
- ✅ Give examples of expected behavior

**Don't:**
- ❌ Be vague ("make it better")
- ❌ Skip important context
- ❌ Assume Claude knows your project structure
- ❌ Forget to specify acceptance criteria

### For System Configuration

**Conservative (Recommended):**
```yaml
max_retries: 3
timeout: 300
backoff_base: 60
daily_budget: 50
```

**Aggressive (More retries, higher cost):**
```yaml
max_retries: 5
timeout: 600
backoff_base: 30
daily_budget: 100
```

**Minimal (Low budget, fast failure):**
```yaml
max_retries: 1
timeout: 180
backoff_base: 120
daily_budget: 20
```

## Future Enhancements

### Planned Features

1. **Smart Retry** - Analyze error patterns to decide retry strategy
2. **Partial Success** - Accept PR even if some tests fail (with flag)
3. **Retry Budgets** - Per-complexity retry limits (simple: 2, complex: 5)
4. **Learning System** - Track which errors Claude can fix vs. can't
5. **Retry Queue** - Separate queue for retries vs. new tasks

## Conclusion

A well-designed retry system is critical for automated development. It must balance:
- **Persistence** - Try hard enough to fix issues
- **Cost Control** - Don't waste money on impossible tasks
- **User Experience** - Fail gracefully and inform clearly
- **System Health** - Don't overwhelm resources

With proper retry logic, the success rate increases from ~60% (no retries) to ~90-95% (with 3 retries), while keeping costs reasonable and turnaround times acceptable.

**Key Takeaways:**
- ✅ Default 3 retries is a sweet spot
- ✅ Always pass error context to Claude on retry
- ✅ Use exponential backoff to avoid tight loops
- ✅ Track metrics to optimize retry strategy
- ✅ Fail gracefully and notify user clearly
- ✅ Budget limits prevent runaway costs
