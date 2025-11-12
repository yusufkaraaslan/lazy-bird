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
