/**
 * Project Header Block
 *
 * Shows project header information and controls
 * Always visible at the top of project view
 */

import { useEffect, useState } from 'react';
import {  Folder, Settings, Play, Pause, Clock, Terminal, AlertCircle, CheckCircle2 } from 'lucide-react';
import { projectsApi } from '../../lib/api';
import { useDashboardStore } from '../../store';
import type { BlockProps } from '../../config/blockRegistry';
import type { Project } from '../../types/api';

export function ProjectHeaderBlock({}: BlockProps) {
  const selectedProjectId = useDashboardStore((state) => state.selectedProjectId);
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    const fetchProject = async () => {
      if (!selectedProjectId) {
        setProject(null);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const response = await projectsApi.get(selectedProjectId);
        setProject(response.data.project);
        setError(null);
      } catch (err: any) {
        console.error('Failed to fetch project:', err);
        setError(err.message || 'Failed to load project');
      } finally {
        setLoading(false);
      }
    };

    fetchProject();
    const interval = setInterval(fetchProject, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, [selectedProjectId]);

  const handleToggleEnabled = async () => {
    if (!project) return;

    try {
      setUpdating(true);
      if (project.enabled) {
        await projectsApi.disable(project.id);
      } else {
        await projectsApi.enable(project.id);
      }

      // Refresh project data
      const response = await projectsApi.get(project.id);
      setProject(response.data.project);
    } catch (err: any) {
      console.error('Failed to toggle project:', err);
      alert(`Failed to ${project.enabled ? 'disable' : 'enable'} project: ${err.message}`);
    } finally {
      setUpdating(false);
    }
  };

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

  if (!project) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <Folder className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No project selected</p>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-r from-primary-50 to-blue-50 dark:from-primary-900/20 dark:to-blue-900/20 rounded-lg p-6 border border-primary-200 dark:border-primary-800">
      <div className="flex items-start justify-between">
        {/* Project Info */}
        <div className="flex items-start gap-4 flex-1">
          <div className={`
            p-3 rounded-lg
            ${project.enabled
              ? 'bg-primary-100 dark:bg-primary-800/50'
              : 'bg-gray-200 dark:bg-gray-700'
            }
          `}>
            <Folder className={`w-8 h-8 ${
              project.enabled
                ? 'text-primary-600 dark:text-primary-400'
                : 'text-gray-500 dark:text-gray-400'
            }`} />
          </div>

          <div className="flex-1">
            {/* Project Name & Type */}
            <div className="flex items-center gap-3 mb-2">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {project.name}
              </h2>
              {project.enabled ? (
                <span className="flex items-center gap-1.5 px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-md text-xs font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Active
                </span>
              ) : (
                <span className="flex items-center gap-1.5 px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-md text-xs font-medium">
                  <Pause className="w-3.5 h-3.5" />
                  Paused
                </span>
              )}
            </div>

            {/* Project Details */}
            <div className="grid grid-cols-2 gap-4 mt-4">
              {/* Type & Framework */}
              <div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Type</div>
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {project.type}
                </div>
              </div>

              {/* Repository */}
              <div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Repository</div>
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                  {project.repository}
                </div>
              </div>

              {/* Test Command */}
              {project.test_command && (
                <div className="col-span-2">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1.5">
                    <Terminal className="w-3 h-3" />
                    Test Command
                  </div>
                  <div className="text-xs font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded text-gray-800 dark:text-gray-200">
                    {project.test_command}
                  </div>
                </div>
              )}

              {/* Build Command */}
              {project.build_command && (
                <div className="col-span-2">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1.5">
                    <Terminal className="w-3 h-3" />
                    Build Command
                  </div>
                  <div className="text-xs font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded text-gray-800 dark:text-gray-200">
                    {project.build_command}
                  </div>
                </div>
              )}
            </div>

            {/* Path */}
            <div className="mt-4 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1.5">
              <Folder className="w-3 h-3" />
              {project.path}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {/* Enable/Disable Toggle */}
          <button
            onClick={handleToggleEnabled}
            disabled={updating}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm
              transition-all duration-200
              ${project.enabled
                ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 hover:bg-yellow-200 dark:hover:bg-yellow-900/40'
                : 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-900/40'
              }
              ${updating ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-sm'}
            `}
          >
            {updating ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
            ) : project.enabled ? (
              <>
                <Pause className="w-4 h-4" />
                Pause
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Enable
              </>
            )}
          </button>

          {/* Settings Button */}
          <button
            className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors duration-200"
            title="Edit project settings"
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Last Activity (placeholder for future enhancement) */}
      <div className="mt-4 pt-4 border-t border-primary-200 dark:border-primary-800">
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <Clock className="w-3.5 h-3.5" />
          <span>Last activity: Coming soon...</span>
        </div>
      </div>
    </div>
  );
}
