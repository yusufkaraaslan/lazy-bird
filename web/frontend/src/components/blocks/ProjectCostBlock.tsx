/**
 * Project Cost Block
 *
 * Shows cost breakdown and spending metrics for the project
 * Includes daily/weekly trends and cost per issue
 */

import { useEffect, useState } from 'react';
import { DollarSign, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';
import { useDashboardStore } from '../../store';
import type { BlockProps } from '../../config/blockRegistry';

interface CostMetrics {
  total_cost: number;
  cost_per_issue: number;
  daily_cost: number;
  weekly_cost: number;
  monthly_cost: number;
  cost_trend: 'up' | 'down' | 'stable';
  trend_percentage: number;
}

export function ProjectCostBlock({}: BlockProps) {
  const selectedProjectId = useDashboardStore((state) => state.selectedProjectId);
  const [costMetrics, setCostMetrics] = useState<CostMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCostMetrics = async () => {
      if (!selectedProjectId) {
        setCostMetrics(null);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);

        // Mock cost data (replace with real API call)
        // TODO: Implement analytics API endpoint for cost metrics
        const mockData: CostMetrics = {
          total_cost: 24.50,
          cost_per_issue: 1.75,
          daily_cost: 3.20,
          weekly_cost: 18.90,
          monthly_cost: 73.50,
          cost_trend: 'down',
          trend_percentage: 12.5,
        };

        setCostMetrics(mockData);
        setError(null);
      } catch (err: any) {
        console.error('Failed to fetch cost metrics:', err);
        setError(err.message || 'Failed to load cost metrics');
      } finally {
        setLoading(false);
      }
    };

    fetchCostMetrics();
    const interval = setInterval(fetchCostMetrics, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [selectedProjectId]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
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

  if (!selectedProjectId || !costMetrics) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <DollarSign className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No project selected</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Total Cost */}
      <div className="p-4 rounded-lg bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border border-green-200 dark:border-green-800">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-xs font-medium text-green-700 dark:text-green-400 mb-1">
              Total Project Cost
            </p>
            <p className="text-3xl font-bold text-green-900 dark:text-green-100">
              {formatCurrency(costMetrics.total_cost)}
            </p>
            <div className="flex items-center gap-2 mt-2">
              {costMetrics.cost_trend === 'down' ? (
                <TrendingDown className="w-4 h-4 text-green-600 dark:text-green-400" />
              ) : costMetrics.cost_trend === 'up' ? (
                <TrendingUp className="w-4 h-4 text-red-600 dark:text-red-400" />
              ) : (
                <span className="w-4 h-0.5 bg-gray-400" />
              )}
              <span className={`text-xs font-medium ${
                costMetrics.cost_trend === 'down'
                  ? 'text-green-700 dark:text-green-400'
                  : costMetrics.cost_trend === 'up'
                  ? 'text-red-700 dark:text-red-400'
                  : 'text-gray-600 dark:text-gray-400'
              }`}>
                {costMetrics.cost_trend === 'down' ? '↓' : costMetrics.cost_trend === 'up' ? '↑' : '→'} {costMetrics.trend_percentage}% vs last period
              </span>
            </div>
          </div>
          <div className="p-3 rounded-full bg-green-100 dark:bg-green-800/50">
            <DollarSign className="w-6 h-6 text-green-600 dark:text-green-400" />
          </div>
        </div>
      </div>

      {/* Cost Breakdown */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600">
          <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Per Issue</p>
          <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {formatCurrency(costMetrics.cost_per_issue)}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Average cost
          </p>
        </div>

        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600">
          <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Daily</p>
          <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {formatCurrency(costMetrics.daily_cost)}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Last 24 hours
          </p>
        </div>

        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600">
          <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Weekly</p>
          <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {formatCurrency(costMetrics.weekly_cost)}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Last 7 days
          </p>
        </div>

        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600">
          <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Monthly</p>
          <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {formatCurrency(costMetrics.monthly_cost)}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Last 30 days
          </p>
        </div>
      </div>

      {/* Cost Optimization Tips */}
      {costMetrics.cost_per_issue > 2.00 && (
        <div className="p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300 mb-1">
                High Cost Per Issue
              </p>
              <p className="text-xs text-yellow-700 dark:text-yellow-400">
                Consider optimizing task complexity or reviewing retry patterns to reduce costs.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Budget Info */}
      <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
        <p className="text-xs font-medium text-blue-700 dark:text-blue-400 mb-1">
          Budget Tracking
        </p>
        <p className="text-xs text-blue-600 dark:text-blue-300">
          Set budget limits and alerts in Settings to control spending.
        </p>
      </div>
    </div>
  );
}
