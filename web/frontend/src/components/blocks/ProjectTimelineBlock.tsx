/**
 * Project Timeline Block
 *
 * Shows a visual timeline of project activity
 * Includes issue creation/completion, agent work, and test runs
 */

import { useEffect, useState } from 'react';
import { GitCommit, CheckCircle2, XCircle, Clock, PlayCircle, AlertCircle } from 'lucide-react';
import { analyticsApi } from '../../lib/api';
import { useDashboardStore } from '../../store';
import type { BlockProps } from '../../config/blockRegistry';
import type { Issue } from '../../types/api';

interface TimelineEvent {
  id: string;
  type: 'issue_created' | 'issue_completed' | 'issue_failed' | 'test_run' | 'agent_work';
  timestamp: string;
  title: string;
  description: string;
  status: 'success' | 'failure' | 'info' | 'warning';
}

export function ProjectTimelineBlock({}: BlockProps) {
  const selectedProjectId = useDashboardStore((state) => state.selectedProjectId);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTimeline = async () => {
      if (!selectedProjectId) {
        setEvents([]);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const response = await analyticsApi.getProject(selectedProjectId);
        const analytics = response.data;

        // Convert recent issues into timeline events
        const timelineEvents: TimelineEvent[] = analytics.recent_issues.map((issue: Issue) => {
          const isDone = issue.status === 'done';
          const isFailed = issue.status === 'failed';

          return {
            id: `issue-${issue.number}`,
            type: isDone ? 'issue_completed' : isFailed ? 'issue_failed' : 'issue_created',
            timestamp: issue.updated_at || issue.created_at,
            title: isDone ? 'Issue Completed' : isFailed ? 'Issue Failed' : 'Issue Created',
            description: `#${issue.number}: ${issue.title}`,
            status: isDone ? 'success' : isFailed ? 'failure' : 'info',
          };
        });

        // Sort by timestamp (newest first)
        timelineEvents.sort((a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
        );

        setEvents(timelineEvents);
        setError(null);
      } catch (err: any) {
        console.error('Failed to fetch timeline:', err);
        setError(err.message || 'Failed to load timeline');
      } finally {
        setLoading(false);
      }
    };

    fetchTimeline();
    const interval = setInterval(fetchTimeline, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [selectedProjectId]);

  const getEventIcon = (type: TimelineEvent['type']) => {
    switch (type) {
      case 'issue_completed':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'issue_failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'test_run':
        return <PlayCircle className="w-4 h-4 text-blue-500" />;
      case 'agent_work':
        return <Clock className="w-4 h-4 text-purple-500" />;
      case 'issue_created':
      default:
        return <GitCommit className="w-4 h-4 text-gray-500" />;
    }
  };

  const getEventColor = (status: TimelineEvent['status']) => {
    switch (status) {
      case 'success':
        return 'border-green-500 bg-green-50 dark:bg-green-900/20';
      case 'failure':
        return 'border-red-500 bg-red-50 dark:bg-red-900/20';
      case 'warning':
        return 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20';
      case 'info':
      default:
        return 'border-blue-500 bg-blue-50 dark:bg-blue-900/20';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
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

  if (!selectedProjectId) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <Clock className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No project selected</p>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <Clock className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No recent activity</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Timeline header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Recent Activity
        </h3>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {events.length} events
        </span>
      </div>

      {/* Timeline list */}
      <div className="relative space-y-3">
        {/* Vertical line */}
        <div className="absolute left-4 top-0 bottom-0 w-px bg-gray-200 dark:bg-gray-700" />

        {events.map((event) => (
          <div key={event.id} className="relative flex gap-3">
            {/* Icon */}
            <div className={`
              relative z-10 flex items-center justify-center w-8 h-8 rounded-full border-2
              ${getEventColor(event.status)}
            `}>
              {getEventIcon(event.type)}
            </div>

            {/* Content */}
            <div className="flex-1 pb-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {event.title}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
                    {event.description}
                  </p>
                </div>
                <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                  {formatTimestamp(event.timestamp)}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
