/**
 * TypeScript types for API responses
 */

export interface Project {
  id: string;
  name: string;
  type: string;
  path: string;
  repository: string;
  git_platform: 'github' | 'gitlab';
  test_command: string | null;
  build_command: string | null;
  lint_command: string | null;
  format_command: string | null;
  enabled: boolean;
}

export interface ProjectCreate {
  name: string;
  type: string;
  path: string;
  repository: string;
  git_platform: 'github' | 'gitlab';
  test_command?: string;
  build_command?: string;
  lint_command?: string;
  format_command?: string;
  enabled: boolean;
}

export interface ServiceStatus {
  name: string;
  status: 'running' | 'stopped' | 'error' | 'unknown';
  loaded: boolean;
  uptime_seconds: number;
  raw_status?: string;
  error?: string;
}

export interface SystemResources {
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  disk_percent: number;
  disk_free_gb: number;
  disk_total_gb: number;
}

export interface SystemStatus {
  services: {
    [serviceName: string]: ServiceStatus;
  };
  resources: SystemResources;
  config: {
    phase: number | string;
    projects_count: number;
  };
}

export interface Task {
  issue_id: number;
  title: string;
  body: string;
  steps: string[];
  complexity: 'simple' | 'medium' | 'complex';
  url: string;
  queued_at?: string;
  priority?: string;
  project_id?: string;
  project_name?: string;
  project_type?: string;
  status?: 'pending' | 'in-progress' | 'completed' | 'completed-no-changes' | 'failed';
  _file?: string;
  _queued_at?: string;
  _size_bytes?: number;
}

export interface QueueStats {
  total_tasks: number;
  by_project: {
    [projectId: string]: number;
  };
  by_complexity: {
    simple: number;
    medium: number;
    complex: number;
    unknown: number;
  };
  queue_dir: string;
}

export interface Issue {
  number: number;
  project_id: string;
  title: string;
  body: string;
  state: 'open' | 'closed';
  status: 'queued' | 'processing' | 'testing' | 'done' | 'failed';
  labels: string[];
  created_at: string;
  updated_at: string;
  url: string;
  author: string;
  complexity?: 'simple' | 'medium' | 'complex';
  progress?: number;
}

export interface Agent {
  agent_id: string;
  pid: number;
  status: 'idle' | 'working' | 'error' | 'stopped';
  current_task?: {
    issue_number: number;
    project_id: string;
    started_at: string;
  };
  started_at: string;
  cpu_percent: number;
  memory_mb: number;
}

export interface OverallAnalytics {
  total_issues: number;
  by_status: {
    queued: number;
    processing: number;
    testing: number;
    done: number;
    failed: number;
  };
  by_complexity: {
    simple: number;
    medium: number;
    complex: number;
  };
  by_project: {
    [projectId: string]: {
      total: number;
      done: number;
      failed: number;
    };
  };
  success_rate: number;
  avg_completion_time_minutes: number;
}

export interface ProjectAnalytics {
  project_id: string;
  total_issues: number;
  by_status: {
    queued: number;
    processing: number;
    testing: number;
    done: number;
    failed: number;
  };
  by_complexity: {
    simple: number;
    medium: number;
    complex: number;
  };
  success_rate: number;
  avg_completion_time_minutes: number;
  recent_issues: Issue[];
}

export interface CostAnalytics {
  today: number;
  this_week: number;
  this_month: number;
  by_project: {
    [projectId: string]: number;
  };
  daily_budget: number;
  monthly_budget: number;
}
