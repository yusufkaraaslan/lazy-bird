/**
 * Queue page - View and manage task queue
 */
import { useState, useEffect } from 'react';
import { useQueue, useQueueStats, useCancelTask } from '../hooks/useQueue';
import { ExternalLink, X, AlertCircle, Clock, FileText } from 'lucide-react';
import type { Task } from '../types/api';

export function QueuePage() {
  const [selectedProject, setSelectedProject] = useState<string | undefined>(undefined);
  const { data: tasks, isLoading, error } = useQueue(selectedProject);
  const { data: stats } = useQueueStats();
  const cancelTask = useCancelTask();

  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="text-gray-600 dark:text-gray-400">Loading queue...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 p-4 rounded-lg">
          <div className="flex items-center gap-2">
            <AlertCircle size={20} />
            <span>Failed to load queue</span>
          </div>
        </div>
      </div>
    );
  }

  const handleCancelTask = async (issueId: number) => {
    if (!confirm('Are you sure you want to cancel this task?')) return;

    try {
      await cancelTask.mutateAsync(issueId.toString());
    } catch (err) {
      console.error('Cancel failed:', err);
    }
  };

  const getComplexityColor = (complexity: string) => {
    switch (complexity) {
      case 'simple':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'complex':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto p-6 lg:p-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Task Queue</h1>
          <p className="text-gray-600 dark:text-gray-400">View and manage queued tasks</p>
        </div>

        {/* Stats Summary */}
        {stats && (
          <div className="mb-8 grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
              <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">Total Tasks</div>
              <div className="text-3xl font-bold text-gray-900 dark:text-white">{stats.total_tasks}</div>
            </div>
            <div className="bg-green-50 dark:bg-green-900/20 p-6 rounded-xl border border-green-200 dark:border-green-700/50 shadow-sm">
              <div className="text-sm font-medium text-green-700 dark:text-green-300 mb-2">Simple</div>
              <div className="text-3xl font-bold text-green-900 dark:text-green-100">{stats.by_complexity.simple}</div>
            </div>
            <div className="bg-yellow-50 dark:bg-yellow-900/20 p-6 rounded-xl border border-yellow-200 dark:border-yellow-700/50 shadow-sm">
              <div className="text-sm font-medium text-yellow-700 dark:text-yellow-300 mb-2">Medium</div>
              <div className="text-3xl font-bold text-yellow-900 dark:text-yellow-100">{stats.by_complexity.medium}</div>
            </div>
            <div className="bg-red-50 dark:bg-red-900/20 p-6 rounded-xl border border-red-200 dark:border-red-700/50 shadow-sm">
              <div className="text-sm font-medium text-red-700 dark:text-red-300 mb-2">Complex</div>
              <div className="text-3xl font-bold text-red-900 dark:text-red-100">{stats.by_complexity.complex}</div>
            </div>
          </div>
        )}

      {/* Filter */}
      {stats && Object.keys(stats.by_project).length > 0 && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Filter by Project
          </label>
          <select
            value={selectedProject || ''}
            onChange={(e) => setSelectedProject(e.target.value || undefined)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">All Projects</option>
            {Object.keys(stats.by_project).map((projectId) => (
              <option key={projectId} value={projectId}>
                {projectId} ({stats.by_project[projectId]} tasks)
              </option>
            ))}
          </select>
        </div>
      )}

        {/* Tasks List */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
          {tasks && tasks.length === 0 ? (
            <div className="text-center py-16">
              <Clock size={56} className="mx-auto text-gray-400 mb-4" />
              <p className="text-lg text-gray-600 dark:text-gray-400 mb-2">No tasks in queue</p>
              <p className="text-sm text-gray-500 dark:text-gray-500">
                Tasks will appear here when added to the queue
              </p>
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900/50">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                    Issue
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                    Title
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                    Project
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                    Complexity
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                    Queued At
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700/50">
              {tasks?.map((task) => (
                <tr key={task.issue_id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      #{task.issue_id}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <button
                      onClick={() => setSelectedTask(task)}
                      className="text-sm text-blue-600 dark:text-blue-400 hover:underline text-left"
                    >
                      {task.title}
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {task.project_name || task.project_id || '-'}
                    </div>
                    {task.project_type && (
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {task.project_type}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs rounded-full ${getComplexityColor(task.complexity)}`}>
                      {task.complexity}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                    {formatDate(task._queued_at || task.queued_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                    <div className="flex justify-end gap-2">
                      {task.url && (
                        <a
                          href={task.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-2 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900 rounded"
                          title="View Issue"
                        >
                          <ExternalLink size={16} />
                        </a>
                      )}
                      <button
                        onClick={() => setSelectedTask(task)}
                        className="p-2 text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                        title="View Details"
                      >
                        <FileText size={16} />
                      </button>
                      <button
                        onClick={() => handleCancelTask(task.issue_id)}
                        disabled={cancelTask.isPending}
                        className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900 rounded disabled:opacity-50"
                        title="Cancel Task"
                      >
                        <X size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Task Details Modal */}
        {selectedTask && (
          <TaskDetailsModal
            task={selectedTask}
            onClose={() => setSelectedTask(null)}
          />
        )}
      </div>
    </div>
  );
}

// Task Details Modal
function TaskDetailsModal({ task, onClose }: { task: Task; onClose: () => void }) {
  const [activeTab, setActiveTab] = useState<'details' | 'logs'>('details');
  const [logs, setLogs] = useState<string | null>(null);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsError, setLogsError] = useState<string | null>(null);

  const fetchLogs = async () => {
    if (!task.project_id || !task.issue_id) return;

    setLogsLoading(true);
    setLogsError(null);
    try {
      const response = await fetch(`http://localhost:5000/api/queue/${task.project_id}/${task.issue_id}/logs`);
      if (!response.ok) {
        if (response.status === 404) {
          setLogsError('No logs found for this task yet');
        } else {
          throw new Error('Failed to fetch logs');
        }
        return;
      }
      const data = await response.json();
      setLogs(data.content || 'No log content available');
    } catch (error) {
      setLogsError('Failed to load logs');
      console.error('Error fetching logs:', error);
    } finally {
      setLogsLoading(false);
    }
  };

  // Fetch logs when logs tab is selected
  useEffect(() => {
    if (activeTab === 'logs' && logs === null && !logsLoading) {
      fetchLogs();
    }
  }, [activeTab]);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] flex flex-col">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                {task.title}
              </h2>
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Issue #{task.issue_id}
                </span>
                <span className={`px-2 py-1 text-xs rounded-full ${
                  task.complexity === 'simple' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                  task.complexity === 'medium' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
                  'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                }`}>
                  {task.complexity}
                </span>
                {task.status && (
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    task.status === 'completed' || task.status === 'completed-no-changes' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                    task.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
                    task.status === 'in-progress' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
                    'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
                  }`}>
                    {task.status}
                  </span>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            >
              <X size={20} />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex gap-4 border-b border-gray-200 dark:border-gray-700">
            <button
              onClick={() => setActiveTab('details')}
              className={`pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'details'
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Details
            </button>
            <button
              onClick={() => setActiveTab('logs')}
              className={`pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'logs'
                  ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Logs
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">{activeTab === 'details' ? (
          <div>

          {/* Project Info */}
          {(task.project_name || task.project_id) && (
            <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Project</div>
              <div className="text-gray-900 dark:text-white">
                {task.project_name || task.project_id}
              </div>
              {task.project_type && (
                <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Type: {task.project_type}
                </div>
              )}
            </div>
          )}

          {/* Task Body */}
          <div className="mb-6">
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Description</div>
            <div className="prose dark:prose-invert max-w-none bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
              <pre className="whitespace-pre-wrap text-sm text-gray-900 dark:text-white">
                {task.body}
              </pre>
            </div>
          </div>

          {/* Steps */}
          {task.steps && task.steps.length > 0 && (
            <div className="mb-6">
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Steps</div>
              <ol className="list-decimal list-inside space-y-2 bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                {task.steps.map((step, index) => (
                  <li key={index} className="text-sm text-gray-900 dark:text-white">
                    {step}
                  </li>
                ))}
              </ol>
            </div>
          )}

          </div>
        ) : (
          <div>
            {/* Logs Tab */}
            {logsLoading ? (
              <div className="text-center py-8 text-gray-600 dark:text-gray-400">
                Loading logs...
              </div>
            ) : logsError ? (
              <div className="text-center py-8 text-gray-600 dark:text-gray-400">
                {logsError}
              </div>
            ) : logs ? (
              <div className="bg-gray-900 dark:bg-black rounded-lg p-4 overflow-auto">
                <pre className="text-sm text-gray-100 font-mono whitespace-pre-wrap">
                  {logs}
                </pre>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-600 dark:text-gray-400">
                No logs available
              </div>
            )}
          </div>
        )}
        </div>

        {/* Actions */}
        <div className="p-6 border-t border-gray-200 dark:border-gray-700">
          <div className="flex justify-end gap-3">
            {task.url && (
              <a
                href={task.url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
              >
                <ExternalLink size={16} />
                View on {task.url.includes('github') ? 'GitHub' : 'GitLab'}
              </a>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
