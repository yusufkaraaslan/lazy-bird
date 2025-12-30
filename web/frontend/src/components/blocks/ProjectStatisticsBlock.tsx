/**
 * Project Statistics Block
 *
 * Shows key statistics and metrics for the selected project
 */

import { useEffect, useState } from 'react';
import { TrendingUp, Target, Clock, RotateCcw, AlertCircle } from 'lucide-react';
import { analyticsApi } from '../../lib/api';
import { useDashboardStore } from '../../store';
import type { BlockProps } from '../../config/blockRegistry';
import type { ProjectAnalytics } from '../../types/api';

export function ProjectStatisticsBlock({}: BlockProps) {
  const selectedProjectId = useDashboardStore((state) => state.selectedProjectId);
  const [analytics, setAnalytics] = useState<ProjectAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      if (!selectedProjectId) {
        setAnalytics(null);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const response = await analyticsApi.getProject(selectedProjectId);
        setAnalytics(response.data);
        setError(null);
      } catch (err: any) {
        console.error('Failed to fetch project analytics:', err);
        setError(err.message || 'Failed to load analytics');
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [selectedProjectId]);

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

  if (!selectedProjectId || !analytics) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <TrendingUp className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No project selected</p>
      </div>
    );
  }

  const stats = [
    {
      label: 'Success Rate',
      value: `${analytics.success_rate.toFixed(1)}%`,
      icon: Target,
      color: analytics.success_rate >= 80 ? 'text-green-600 dark:text-green-400' : analytics.success_rate >= 60 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400',
      bgColor: analytics.success_rate >= 80 ? 'bg-green-100 dark:bg-green-900/30' : analytics.success_rate >= 60 ? 'bg-yellow-100 dark:bg-yellow-900/30' : 'bg-red-100 dark:bg-red-900/30',
      description: `${analytics.by_status.done} done, ${analytics.by_status.failed} failed`,
    },
    {
      label: 'Avg Time',
      value: analytics.avg_completion_time_minutes < 60
        ? `${Math.round(analytics.avg_completion_time_minutes)}m`
        : `${(analytics.avg_completion_time_minutes / 60).toFixed(1)}h`,
      icon: Clock,
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-100 dark:bg-blue-900/30',
      description: 'Average completion time',
    },
    {
      label: 'Total Issues',
      value: analytics.total_issues.toString(),
      icon: TrendingUp,
      color: 'text-purple-600 dark:text-purple-400',
      bgColor: 'bg-purple-100 dark:bg-purple-900/30',
      description: `${analytics.by_status.queued + analytics.by_status.processing} active`,
    },
  ];

  // Calculate retry rate (if we have the data)
  const totalCompleted = analytics.by_status.done + analytics.by_status.failed;
  const retryRate = totalCompleted > 0 ? ((analytics.by_status.failed / totalCompleted) * 100) : 0;

  if (totalCompleted > 0) {
    stats.push({
      label: 'Retry Rate',
      value: `${retryRate.toFixed(1)}%`,
      icon: RotateCcw,
      color: retryRate < 10 ? 'text-green-600 dark:text-green-400' : retryRate < 25 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400',
      bgColor: retryRate < 10 ? 'bg-green-100 dark:bg-green-900/30' : retryRate < 25 ? 'bg-yellow-100 dark:bg-yellow-900/30' : 'bg-red-100 dark:bg-red-900/30',
      description: 'Failed tasks requiring retry',
    });
  }

  return (
    <div className="space-y-4">
      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3">
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div
              key={index}
              className="p-4 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600"
            >
              <div className="flex items-start justify-between mb-2">
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  {stat.label}
                </span>
                <div className={`p-1.5 rounded-md ${stat.bgColor}`}>
                  <Icon className={`w-4 h-4 ${stat.color}`} />
                </div>
              </div>
              <div className={`text-2xl font-bold ${stat.color} mb-1`}>
                {stat.value}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {stat.description}
              </div>
            </div>
          );
        })}
      </div>

      {/* Complexity breakdown */}
      <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600">
        <div className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-3">
          Complexity Distribution
        </div>
        <div className="space-y-2">
          {['simple', 'medium', 'complex'].map((complexity) => {
            const count = analytics.by_complexity[complexity as keyof typeof analytics.by_complexity] || 0;
            const percentage = analytics.total_issues > 0 ? (count / analytics.total_issues) * 100 : 0;

            const colors = {
              simple: 'bg-gray-400 dark:bg-gray-500',
              medium: 'bg-blue-500 dark:bg-blue-600',
              complex: 'bg-purple-500 dark:bg-purple-600',
            };

            return (
              <div key={complexity}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-gray-700 dark:text-gray-300 capitalize">
                    {complexity}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {count} ({percentage.toFixed(0)}%)
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                  <div
                    className={`${colors[complexity as keyof typeof colors]} h-2 rounded-full transition-all duration-300`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Status breakdown */}
      <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600">
        <div className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-3">
          Status Breakdown
        </div>
        <div className="grid grid-cols-3 gap-2">
          {[
            { key: 'queued', label: 'Queued', color: 'text-yellow-600 dark:text-yellow-400' },
            { key: 'processing', label: 'Processing', color: 'text-blue-600 dark:text-blue-400' },
            { key: 'testing', label: 'Testing', color: 'text-indigo-600 dark:text-indigo-400' },
            { key: 'done', label: 'Done', color: 'text-green-600 dark:text-green-400' },
            { key: 'failed', label: 'Failed', color: 'text-red-600 dark:text-red-400' },
          ].map((status) => {
            const count = analytics.by_status[status.key as keyof typeof analytics.by_status] || 0;
            return (
              <div key={status.key} className="text-center">
                <div className={`text-lg font-bold ${status.color}`}>
                  {count}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {status.label}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
