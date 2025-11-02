#!/usr/bin/env python3
"""
Lazy_Bird Issue Watcher Service
Polls GitHub/GitLab for issues labeled 'ready' and queues them for processing
"""

import time
import sys
import json
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('issue-watcher')


class IssueWatcher:
    """Monitors GitHub/GitLab for ready-to-process issues"""

    def __init__(self, config_path: Path):
        """Initialize watcher with configuration"""
        self.config_path = config_path
        self.config = self.load_config()

        # Platform and repository
        self.platform = self.config.get('git_platform', 'github')
        self.repository = self.config.get('repository', '')

        # Load API token
        self.token = self.load_token()

        # Polling configuration
        self.poll_interval = self.config.get('poll_interval_seconds', 60)

        # State management
        self.processed_issues = self.load_processed_issues()

        # Validate configuration
        self.validate_config()

        logger.info(f"Issue Watcher initialized")
        logger.info(f"  Platform: {self.platform}")
        logger.info(f"  Repository: {self.repository}")
        logger.info(f"  Poll interval: {self.poll_interval}s")

    def load_config(self) -> Dict:
        """Load configuration from YAML or JSON file"""
        if not self.config_path.exists():
            logger.error(f"Configuration file not found: {self.config_path}")
            sys.exit(1)

        try:
            # Support both YAML and JSON
            config_text = self.config_path.read_text()

            if self.config_path.suffix in ['.yml', '.yaml']:
                try:
                    import yaml
                    return yaml.safe_load(config_text)
                except ImportError:
                    logger.error("PyYAML not installed. Install with: pip3 install pyyaml")
                    sys.exit(1)
            else:
                return json.loads(config_text)

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            sys.exit(1)

    def load_token(self) -> str:
        """Load API token from secrets directory"""
        secrets_dir = Path.home() / '.config' / 'lazy_birtd' / 'secrets'

        # Try platform-specific token first
        token_file = secrets_dir / f'{self.platform}_token'
        if not token_file.exists():
            # Fall back to generic api_token
            token_file = secrets_dir / 'api_token'

        if not token_file.exists():
            logger.error(f"API token not found at: {token_file}")
            logger.error("Create token file with: echo 'YOUR_TOKEN' > ~/.config/lazy_birtd/secrets/api_token")
            logger.error("Set permissions: chmod 600 ~/.config/lazy_birtd/secrets/api_token")
            sys.exit(1)

        try:
            token = token_file.read_text().strip()
            if not token:
                logger.error(f"Token file is empty: {token_file}")
                sys.exit(1)
            return token
        except Exception as e:
            logger.error(f"Failed to read token: {e}")
            sys.exit(1)

    def load_processed_issues(self) -> Set[int]:
        """Load set of already-processed issue IDs"""
        data_dir = Path.home() / '.config' / 'lazy_birtd' / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)

        processed_file = data_dir / 'processed_issues.json'
        if processed_file.exists():
            try:
                data = json.loads(processed_file.read_text())
                return set(data)
            except Exception as e:
                logger.warning(f"Failed to load processed issues: {e}")
                return set()
        return set()

    def save_processed_issues(self):
        """Save processed issue IDs to disk"""
        data_dir = Path.home() / '.config' / 'lazy_birtd' / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)

        processed_file = data_dir / 'processed_issues.json'
        try:
            processed_file.write_text(json.dumps(list(self.processed_issues), indent=2))
        except Exception as e:
            logger.error(f"Failed to save processed issues: {e}")

    def validate_config(self):
        """Validate required configuration values"""
        if not self.repository:
            logger.error("Repository not configured in config file")
            sys.exit(1)

        if self.platform not in ['github', 'gitlab']:
            logger.error(f"Unsupported platform: {self.platform}")
            sys.exit(1)

    def fetch_ready_issues(self) -> List[Dict]:
        """Fetch issues with 'ready' label from GitHub/GitLab"""
        try:
            if self.platform == 'github':
                return self.fetch_github_issues()
            elif self.platform == 'gitlab':
                return self.fetch_gitlab_issues()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching issues: {e}")
            return []

    def fetch_github_issues(self) -> List[Dict]:
        """Fetch from GitHub API"""
        # Parse owner/repo from repository URL or string
        repo_parts = self.repository.rstrip('/').split('/')
        owner = repo_parts[-2]
        repo = repo_parts[-1]

        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        params = {
            'labels': 'ready',
            'state': 'open',
            'sort': 'created',
            'direction': 'asc'
        }

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        issues = []
        for issue in response.json():
            # Skip pull requests (they appear as issues in GitHub API)
            if 'pull_request' in issue:
                continue

            issues.append({
                'id': issue['number'],
                'title': issue['title'],
                'body': issue['body'] or '',
                'labels': [l['name'] for l in issue['labels']],
                'url': issue['html_url'],
                'created_at': issue['created_at']
            })

        return issues

    def fetch_gitlab_issues(self) -> List[Dict]:
        """Fetch from GitLab API"""
        # Get project ID from config or parse from URL
        project_id = self.config.get('project_id')

        if not project_id:
            # Try to get project ID from API using project path
            project_path = self.repository.rstrip('/').split('/')[-2:]
            project_path_str = '/'.join(project_path)

            url = f"https://gitlab.com/api/v4/projects/{requests.utils.quote(project_path_str, safe='')}"
            headers = {'PRIVATE-TOKEN': self.token}

            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                project_id = response.json()['id']
            except Exception as e:
                logger.error(f"Failed to get GitLab project ID: {e}")
                return []

        url = f"https://gitlab.com/api/v4/projects/{project_id}/issues"
        headers = {'PRIVATE-TOKEN': self.token}
        params = {
            'labels': 'ready',
            'state': 'opened',
            'order_by': 'created_at',
            'sort': 'asc'
        }

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        issues = []
        for issue in response.json():
            issues.append({
                'id': issue['iid'],
                'title': issue['title'],
                'body': issue['description'] or '',
                'labels': issue['labels'],
                'url': issue['web_url'],
                'created_at': issue['created_at']
            })

        return issues

    def parse_issue(self, issue: Dict) -> Dict:
        """Extract structured data from issue"""
        body = issue['body']

        # Extract complexity from labels or body
        complexity = 'medium'  # default
        for label in issue['labels']:
            if label in ['simple', 'medium', 'complex']:
                complexity = label
                break

        # Parse sections from markdown body
        sections = self.parse_markdown_sections(body)

        # Extract detailed steps
        steps = sections.get('Detailed Steps', [])

        # Extract acceptance criteria
        acceptance_criteria = sections.get('Acceptance Criteria', [])

        return {
            'issue_id': issue['id'],
            'title': issue['title'],
            'body': body,
            'steps': steps,
            'acceptance_criteria': acceptance_criteria,
            'complexity': complexity,
            'url': issue['url'],
            'queued_at': datetime.utcnow().isoformat(),
            'platform': self.platform,
            'repository': self.repository
        }

    def parse_markdown_sections(self, body: str) -> Dict[str, List[str]]:
        """Parse markdown body into sections"""
        sections = {}
        current_section = None
        current_content = []

        for line in body.split('\n'):
            # Check for section headers (## Header)
            if line.strip().startswith('##'):
                # Save previous section
                if current_section:
                    sections[current_section] = current_content

                # Start new section
                current_section = line.strip().lstrip('#').strip()
                current_content = []
            elif current_section:
                # Add content to current section
                stripped = line.strip()
                if stripped and (stripped.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '-', '*', '[ ]', '[x]'))):
                    current_content.append(stripped)

        # Save last section
        if current_section:
            sections[current_section] = current_content

        return sections

    def queue_task(self, parsed_issue: Dict):
        """Add task to processing queue"""
        queue_dir = Path('/var/lib/lazy_birtd/queue')

        # Create queue directory if it doesn't exist
        try:
            queue_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Fall back to user directory if /var/lib not writable
            queue_dir = Path.home() / '.config' / 'lazy_birtd' / 'queue'
            queue_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Using fallback queue directory: {queue_dir}")

        task_file = queue_dir / f"task-{parsed_issue['issue_id']}.json"

        try:
            task_file.write_text(json.dumps(parsed_issue, indent=2))
            logger.info(f"✅ Queued task #{parsed_issue['issue_id']}: {parsed_issue['title']}")
        except Exception as e:
            logger.error(f"Failed to queue task: {e}")
            raise

    def update_issue_labels(self, issue: Dict):
        """Remove 'ready' label and add 'in-queue' label"""
        try:
            if self.platform == 'github':
                self.update_github_labels(issue)
            elif self.platform == 'gitlab':
                self.update_gitlab_labels(issue)
        except Exception as e:
            logger.error(f"Failed to update labels for issue #{issue['id']}: {e}")

    def update_github_labels(self, issue: Dict):
        """Update GitHub issue labels using gh CLI"""
        import subprocess

        repo_parts = self.repository.rstrip('/').split('/')
        owner = repo_parts[-2]
        repo = repo_parts[-1]
        repo_name = f"{owner}/{repo}"

        try:
            # Remove 'ready' label using gh CLI
            result = subprocess.run(
                ['gh', 'issue', 'edit', str(issue['id']), '--repo', repo_name, '--remove-label', 'ready'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                logger.warning(f"Failed to remove 'ready' label: {result.stderr}")

            # Add 'in-queue' label using gh CLI
            result = subprocess.run(
                ['gh', 'issue', 'edit', str(issue['id']), '--repo', repo_name, '--add-label', 'in-queue'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                logger.warning(f"Failed to add 'in-queue' label: {result.stderr}")
            else:
                logger.info(f"✅ Labels updated: ready → in-queue")

        except subprocess.TimeoutExpired:
            logger.error("Timeout updating labels via gh CLI")
        except Exception as e:
            logger.error(f"Error updating labels: {e}")

    def update_gitlab_labels(self, issue: Dict):
        """Update GitLab issue labels"""
        project_id = self.config.get('project_id')
        if not project_id:
            logger.warning("GitLab project_id not configured, cannot update labels")
            return

        headers = {'PRIVATE-TOKEN': self.token}

        # Get current labels
        current_labels = [l for l in issue['labels'] if l != 'ready']
        current_labels.append('processing')

        # Update issue with new labels
        url = f"https://gitlab.com/api/v4/projects/{project_id}/issues/{issue['id']}"
        data = {'labels': ','.join(current_labels)}
        response = requests.put(url, headers=headers, json=data, timeout=30)

        if response.status_code not in [200, 201]:
            logger.warning(f"Failed to update GitLab labels: {response.status_code}")

    def run(self):
        """Main loop - poll for issues and process them"""
        logger.info(f"🔍 Issue Watcher started - monitoring {self.platform}")
        logger.info(f"   Repository: {self.repository}")
        logger.info(f"   Polling every {self.poll_interval} seconds")
        logger.info(f"   Press Ctrl+C to stop")
        logger.info("")

        while True:
            try:
                # Fetch issues with 'ready' label
                issues = self.fetch_ready_issues()

                # Filter out already-processed issues
                new_issues = [i for i in issues if i['id'] not in self.processed_issues]

                if new_issues:
                    logger.info(f"Found {len(new_issues)} new task(s) to process")

                # Process each new issue
                for issue in new_issues:
                    logger.info(f"Processing issue #{issue['id']}: {issue['title']}")

                    # Parse issue into task format
                    parsed = self.parse_issue(issue)

                    # Queue the task
                    self.queue_task(parsed)

                    # Update labels on the issue
                    self.update_issue_labels(issue)

                    # Mark as processed
                    self.processed_issues.add(issue['id'])
                    self.save_processed_issues()

                    logger.info(f"✅ Issue #{issue['id']} queued and labeled 'processing'")

                # Sleep until next poll
                time.sleep(self.poll_interval)

            except KeyboardInterrupt:
                logger.info("\n👋 Shutting down gracefully...")
                break
            except Exception as e:
                logger.error(f"❌ Unexpected error in main loop: {e}")
                logger.info(f"Retrying in {self.poll_interval} seconds...")
                time.sleep(self.poll_interval)


def main():
    """Entry point"""
    # Look for config file
    config_path = Path.home() / '.config' / 'lazy_birtd' / 'config.yml'

    # Also check for .json extension
    if not config_path.exists():
        config_path = Path.home() / '.config' / 'lazy_birtd' / 'config.json'

    if not config_path.exists():
        logger.error("Configuration file not found")
        logger.error(f"Expected: ~/.config/lazy_birtd/config.yml")
        logger.error("")
        logger.error("Create configuration with:")
        logger.error("  mkdir -p ~/.config/lazy_birtd")
        logger.error("  cat > ~/.config/lazy_birtd/config.yml << 'EOF'")
        logger.error("  git_platform: github")
        logger.error("  repository: https://github.com/owner/repo")
        logger.error("  poll_interval_seconds: 60")
        logger.error("  EOF")
        sys.exit(1)

    # Create and run watcher
    watcher = IssueWatcher(config_path)
    watcher.run()


if __name__ == '__main__':
    main()
