/**
 * Cost Tracker Block
 *
 * Shows spending metrics and budget progress
 */

import { useEffect, useState } from 'react';
import { DollarSign, TrendingUp, TrendingDown, AlertTriangle, AlertCircle } from 'lucide-react';
import { analyticsApi } from '../../lib/api';
import type { BlockProps } from '../../config/blockRegistry';
import type { CostAnalytics } from '../../types/api';

export function CostTrackerBlock({}: BlockProps) {
  const [costs, setCosts] = useState<CostAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const costsRes = await analyticsApi.getCosts();
      setCosts(costsRes.data);
      setError(null);
    } catch (err: any) {
      console.error('Failed to fetch costs:', err);
      setError(err.message || 'Failed to load cost data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30 seconds
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

  if (!costs) return null;

  // Handle missing budget fields gracefully with defaults
  const dailyBudget = costs.daily_budget || 50; // Default $50/day
  const monthlyBudget = costs.monthly_budget || 1500; // Default $1500/month

  const monthlyProgress = (costs.this_month / monthlyBudget) * 100;
  const dailyProgress = (costs.today / dailyBudget) * 100;

  const getProgressColor = (progress: number) => {
    if (progress >= 100) return 'bg-red-500';
    if (progress >= 80) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getAlertIcon = () => {
    if (monthlyProgress >= 100 || dailyProgress >= 100) {
      return <AlertTriangle className="w-5 h-5 text-red-500" />;
    }
    if (monthlyProgress >= 80 || dailyProgress >= 80) {
      return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
    }
    return null;
  };

  return (
    <div className="space-y-4">
      {/* Alert */}
      {(monthlyProgress >= 80 || dailyProgress >= 80) && (
        <div className={`flex items-center gap-2 p-3 rounded-lg ${
          monthlyProgress >= 100 || dailyProgress >= 100
            ? 'bg-red-50 dark:bg-red-900/20'
            : 'bg-yellow-50 dark:bg-yellow-900/20'
        }`}>
          {getAlertIcon()}
          <span className={`text-sm font-medium ${
            monthlyProgress >= 100 || dailyProgress >= 100
              ? 'text-red-700 dark:text-red-400'
              : 'text-yellow-700 dark:text-yellow-400'
          }`}>
            {monthlyProgress >= 100 || dailyProgress >= 100
              ? 'Budget limit exceeded!'
              : 'Approaching budget limit'}
          </span>
        </div>
      )}

      {/* Cost summary */}
      <div className="grid grid-cols-3 gap-4">
        <div>
          <div className="flex items-center gap-1.5 mb-1">
            <DollarSign className="w-4 h-4 text-gray-400" />
            <span className="text-xs text-gray-500 dark:text-gray-400">Today</span>
          </div>
          <div className="text-xl font-bold text-gray-900 dark:text-gray-100">
            ${costs.today.toFixed(2)}
          </div>
        </div>

        <div>
          <div className="flex items-center gap-1.5 mb-1">
            <TrendingUp className="w-4 h-4 text-gray-400" />
            <span className="text-xs text-gray-500 dark:text-gray-400">This Week</span>
          </div>
          <div className="text-xl font-bold text-gray-900 dark:text-gray-100">
            ${costs.this_week.toFixed(2)}
          </div>
        </div>

        <div>
          <div className="flex items-center gap-1.5 mb-1">
            <TrendingDown className="w-4 h-4 text-gray-400" />
            <span className="text-xs text-gray-500 dark:text-gray-400">This Month</span>
          </div>
          <div className="text-xl font-bold text-gray-900 dark:text-gray-100">
            ${costs.this_month.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Budget progress */}
      <div className="space-y-3">
        {/* Daily budget */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-gray-600 dark:text-gray-400">
              Daily Budget
            </span>
            <span className="text-xs font-medium text-gray-900 dark:text-gray-100">
              {dailyProgress.toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${getProgressColor(dailyProgress)}`}
              style={{ width: `${Math.min(dailyProgress, 100)}%` }}
            />
          </div>
          <div className="flex items-center justify-between mt-1">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              ${costs.today.toFixed(2)}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              ${dailyBudget.toFixed(2)}
            </span>
          </div>
        </div>

        {/* Monthly budget */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-gray-600 dark:text-gray-400">
              Monthly Budget
            </span>
            <span className="text-xs font-medium text-gray-900 dark:text-gray-100">
              {monthlyProgress.toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${getProgressColor(monthlyProgress)}`}
              style={{ width: `${Math.min(monthlyProgress, 100)}%` }}
            />
          </div>
          <div className="flex items-center justify-between mt-1">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              ${costs.this_month.toFixed(2)}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              ${monthlyBudget.toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {/* Cost by project */}
      {Object.keys(costs.by_project).length > 0 && (
        <div>
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-2">
            By Project
          </div>
          <div className="space-y-2">
            {Object.entries(costs.by_project)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 5)
              .map(([projectId, cost]) => (
                <div
                  key={projectId}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-gray-700 dark:text-gray-300 truncate flex-1">
                    {projectId}
                  </span>
                  <span className="font-medium text-gray-900 dark:text-gray-100 ml-2">
                    ${cost.toFixed(2)}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
