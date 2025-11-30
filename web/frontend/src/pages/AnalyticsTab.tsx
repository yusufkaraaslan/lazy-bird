/**
 * AnalyticsTab Page
 *
 * Analytics and metrics visualization
 * Will contain charts, graphs, and performance metrics
 */

import { ViewSelector } from '../components/ViewSelector';
import { BarChart3 } from 'lucide-react';

export function AnalyticsTab() {
  return (
    <div className="flex flex-col h-full">
      <ViewSelector />
      <div className="flex-1 overflow-y-auto p-6">
        {/* Placeholder - will be replaced with actual analytics in Issue #41 */}
        <div className="flex flex-col items-center justify-center h-full text-center">
          <div className="w-20 h-20 mb-6 rounded-full bg-gradient-primary flex items-center justify-center shadow-glow">
            <BarChart3 className="w-10 h-10 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            Analytics Dashboard
          </h2>
          <p className="text-gray-600 dark:text-gray-400 max-w-md">
            Task metrics, success rates, cost tracking, and performance analytics will appear here.
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-500 mt-4">
            Coming in Issue #41
          </p>
        </div>
      </div>
    </div>
  );
}
