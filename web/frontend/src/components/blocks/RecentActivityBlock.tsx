/**
 * Recent Activity Block
 *
 * Shows timeline of recent events across all projects
 */

import { useEffect, useState } from 'react';
import { Activity, CheckCircle2, XCircle, PlayCircle, AlertCircle } from 'lucide-react';
import { issuesApi } from '../../lib/api';
import type { BlockProps } from '../../config/blockRegistry';
import type { Issue } from '../../types/api';

interface ActivityEvent {
  id: string;
  type: 'issue_status' | 'test_result' | 'pr_created';
  timestamp: string;
  description: string;
  icon: any;
  color: string;
  bg: string;
}

export function RecentActivityBlock({}: BlockProps) {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const issuesRes = await issuesApi.list({ limit: 10 });
      const issues: Issue[] = issuesRes.data.issues || [];

      // Convert issues to activity events
      const activityEvents: ActivityEvent[] = issues.map((issue) => {
        let type: ActivityEvent['type'] = 'issue_status';
        let icon = Activity;
        let color = 'text-blue-500';
        let bg = 'bg-blue-50 dark:bg-blue-900/20';
        let description = '';

        switch (issue.status) {
          case 'processing':
            icon = PlayCircle;
            color = 'text-purple-500';
            bg = 'bg-purple-50 dark:bg-purple-900/20';
            description = `Issue #${issue.number} started processing`;
            break;
          case 'testing':
            type = 'test_result';
            icon = Activity;
            color = 'text-yellow-500';
            bg = 'bg-yellow-50 dark:bg-yellow-900/20';
            description = `Issue #${issue.number} entered testing phase`;
            break;
          case 'done':
            icon = CheckCircle2;
            color = 'text-green-500';
            bg = 'bg-green-50 dark:bg-green-900/20';
            description = `Issue #${issue.number} completed successfully`;
            break;
          case 'failed':
            icon = XCircle;
            color = 'text-red-500';
            bg = 'bg-red-50 dark:bg-red-900/20';
            description = `Issue #${issue.number} failed`;
            break;
          default:
            description = `Issue #${issue.number} queued`;
        }

        return {
          id: `${issue.project_id}-${issue.number}`,
          type,
          timestamp: issue.updated_at,
          description,
          icon,
          color,
          bg,
        };
      });

      setEvents(activityEvents);
      setError(null);
    } catch (err: any) {
      console.error('Failed to fetch activity:', err);
      setError(err.message || 'Failed to load activity');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
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

  if (events.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <Activity className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No recent activity</p>
      </div>
    );
  }

  const formatTime = (isoDate: string) => {
    const date = new Date(isoDate);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const hours = Math.floor(diffMins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  return (
    <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
      {events.map((event) => {
        const Icon = event.icon;
        return (
          <div key={event.id} className="flex items-start gap-3">
            <div className={`p-2 rounded-lg ${event.bg} flex-shrink-0`}>
              <Icon className={`w-4 h-4 ${event.color}`} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm text-gray-900 dark:text-gray-100">
                {event.description}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                {formatTime(event.timestamp)}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
