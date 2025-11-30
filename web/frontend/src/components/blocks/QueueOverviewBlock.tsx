/**
 * Queue Overview Block
 *
 * Shows all tasks across all projects with status breakdown
 */

import { useEffect, useState } from 'react';
import { Clock, PlayCircle, TestTube2, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { issuesApi } from '../../lib/api';
import type { BlockProps } from '../../config/blockRegistry';
import type { Issue } from '../../types/api';

interface QueueStats {
  total: number;
  queued: number;
  processing: number;
  testing: number;
  done: number;
  failed: number;
}

export function QueueOverviewBlock({}: BlockProps) {
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const issuesRes = await issuesApi.list({ limit: 50 });
      const allIssues: Issue[] = issuesRes.data.issues || [];

      const statsData = {
        total: allIssues.length,
        queued: allIssues.filter((i) => i.status === 'queued').length,
        processing: allIssues.filter((i) => i.status === 'processing').length,
        testing: allIssues.filter((i) => i.status === 'testing').length,
        done: allIssues.filter((i) => i.status === 'done').length,
        failed: allIssues.filter((i) => i.status === 'failed').length,
      };

      setStats(statsData);
      setIssues(allIssues.slice(0, 5)); // Show top 5
      setError(null);
    } catch (err: any) {
      console.error('Failed to fetch queue:', err);
      setError(err.message || 'Failed to load queue');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
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

  if (!stats) return null;

  const statusItems = [
    { label: 'Queued', count: stats.queued, icon: Clock, color: 'text-blue-500', bg: 'bg-blue-50 dark:bg-blue-900/20' },
    { label: 'Processing', count: stats.processing, icon: PlayCircle, color: 'text-purple-500', bg: 'bg-purple-50 dark:bg-purple-900/20' },
    { label: 'Testing', count: stats.testing, icon: TestTube2, color: 'text-yellow-500', bg: 'bg-yellow-50 dark:bg-yellow-900/20' },
    { label: 'Done', count: stats.done, icon: CheckCircle2, color: 'text-green-500', bg: 'bg-green-50 dark:bg-green-900/20' },
    { label: 'Failed', count: stats.failed, icon: XCircle, color: 'text-red-500', bg: 'bg-red-50 dark:bg-red-900/20' },
  ];

  return (
    <div className="space-y-4">
      {/* Status breakdown */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {statusItems.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="flex items-center gap-2">
              <div className={`p-1.5 rounded ${item.bg}`}>
                <Icon className={`w-4 h-4 ${item.color}`} />
              </div>
              <div>
                <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
                  {item.count}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {item.label}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent issues */}
      {issues.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
            Recent Issues
          </div>
          {issues.map((issue) => (
            <div
              key={`${issue.project_id}-${issue.number}`}
              className="flex items-center justify-between p-2 rounded bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                  #{issue.number}: {issue.title}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {issue.project_id}
                </div>
              </div>
              <div className={`text-xs px-2 py-1 rounded-full ${
                issue.status === 'done'
                  ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                  : issue.status === 'failed'
                  ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                  : issue.status === 'processing'
                  ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400'
                  : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
              }`}>
                {issue.status}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
