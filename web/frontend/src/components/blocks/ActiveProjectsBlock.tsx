/**
 * Active Projects Block
 *
 * Shows all enabled projects with status and issue counts
 */

import { useEffect, useState } from 'react';
import { FolderOpen, CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';
import { projectsApi, issuesApi } from '../../lib/api';
import type { BlockProps } from '../../config/blockRegistry';
import type { Project } from '../../types/api';

interface ProjectWithStats extends Project {
  total_issues: number;
  status: 'active' | 'paused' | 'error';
}

export function ActiveProjectsBlock({}: BlockProps) {
  const [projects, setProjects] = useState<ProjectWithStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const projectsRes = await projectsApi.list();
      const allProjects: Project[] = projectsRes.data.projects || [];

      // Get issue counts for each project
      const projectsWithStats = await Promise.all(
        allProjects
          .filter((p) => p.enabled)
          .map(async (project) => {
            try {
              const issuesRes = await issuesApi.list({ project_id: project.id });
              const issues = issuesRes.data.issues || [];

              // Determine project status
              let status: 'active' | 'paused' | 'error' = 'active';
              if (!project.enabled) status = 'paused';
              if (issues.some((i: any) => i.status === 'failed')) status = 'error';

              return {
                ...project,
                total_issues: issues.length,
                status,
              };
            } catch (err) {
              return {
                ...project,
                total_issues: 0,
                status: 'error' as const,
              };
            }
          })
      );

      setProjects(projectsWithStats);
      setError(null);
    } catch (err: any) {
      console.error('Failed to fetch projects:', err);
      setError(err.message || 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
        <AlertCircle className="w-5 h-5 text-red-500" />
        <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <FolderOpen className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No active projects</p>
      </div>
    );
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'paused':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'text-green-600 dark:text-green-400';
      case 'paused':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'error':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  return (
    <div className="space-y-3">
      {projects.map((project) => (
        <div
          key={project.id}
          className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
        >
          <div className="flex items-center gap-3 flex-1">
            <FolderOpen className="w-5 h-5 text-primary-500" />
            <div>
              <div className="font-medium text-gray-900 dark:text-gray-100">
                {project.name}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {project.type}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                {project.total_issues}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                issues
              </div>
            </div>

            <div className={`flex items-center gap-1.5 ${getStatusColor(project.status)}`}>
              {getStatusIcon(project.status)}
              <span className="text-xs font-medium capitalize">
                {project.status}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
