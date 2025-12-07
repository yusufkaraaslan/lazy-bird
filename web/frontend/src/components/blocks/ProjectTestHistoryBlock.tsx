/**
 * Project Test History Block
 *
 * Shows test pass/fail trends and recent test results
 * Includes flakiness detection
 */

import { useEffect, useState } from 'react';
import { FlaskConical, CheckCircle2, XCircle, AlertTriangle, TrendingUp } from 'lucide-react';
import { useDashboardStore } from '../../store';
import type { BlockProps } from '../../config/blockRegistry';

interface TestResult {
  id: string;
  issue_number: number;
  timestamp: string;
  passed: boolean;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  duration_seconds: number;
}

export function ProjectTestHistoryBlock({}: BlockProps) {
  const selectedProjectId = useDashboardStore((state) => state.selectedProjectId);
  const [testHistory, setTestHistory] = useState<TestResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTestHistory = async () => {
      if (!selectedProjectId) {
        setTestHistory([]);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);

        // Mock test history data (replace with real API call)
        // TODO: Implement analytics API endpoint for test history
        const mockData: TestResult[] = [
          {
            id: '1',
            issue_number: 45,
            timestamp: new Date(Date.now() - 3600000).toISOString(),
            passed: true,
            total_tests: 12,
            passed_tests: 12,
            failed_tests: 0,
            duration_seconds: 45,
          },
          {
            id: '2',
            issue_number: 44,
            timestamp: new Date(Date.now() - 7200000).toISOString(),
            passed: true,
            total_tests: 10,
            passed_tests: 10,
            failed_tests: 0,
            duration_seconds: 38,
          },
          {
            id: '3',
            issue_number: 43,
            timestamp: new Date(Date.now() - 10800000).toISOString(),
            passed: false,
            total_tests: 8,
            passed_tests: 6,
            failed_tests: 2,
            duration_seconds: 52,
          },
          {
            id: '4',
            issue_number: 42,
            timestamp: new Date(Date.now() - 14400000).toISOString(),
            passed: true,
            total_tests: 15,
            passed_tests: 15,
            failed_tests: 0,
            duration_seconds: 62,
          },
          {
            id: '5',
            issue_number: 41,
            timestamp: new Date(Date.now() - 18000000).toISOString(),
            passed: true,
            total_tests: 9,
            passed_tests: 9,
            failed_tests: 0,
            duration_seconds: 41,
          },
        ];

        setTestHistory(mockData);
        setError(null);
      } catch (err: any) {
        console.error('Failed to fetch test history:', err);
        setError(err.message || 'Failed to load test history');
      } finally {
        setLoading(false);
      }
    };

    fetchTestHistory();
    const interval = setInterval(fetchTestHistory, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [selectedProjectId]);

  // Calculate statistics
  const passRate = testHistory.length > 0
    ? (testHistory.filter(t => t.passed).length / testHistory.length) * 100
    : 0;

  const avgDuration = testHistory.length > 0
    ? testHistory.reduce((sum, t) => sum + t.duration_seconds, 0) / testHistory.length
    : 0;

  const totalTests = testHistory.reduce((sum, t) => sum + t.total_tests, 0);

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffHours < 1) return 'Just now';
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
        <AlertTriangle className="w-5 h-5 text-red-500" />
        <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
      </div>
    );
  }

  if (!selectedProjectId) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <FlaskConical className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No project selected</p>
      </div>
    );
  }

  if (testHistory.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <FlaskConical className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No test history available</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-600 dark:text-gray-400">Pass Rate</span>
            <TrendingUp className={`w-3.5 h-3.5 ${passRate >= 80 ? 'text-green-500' : passRate >= 60 ? 'text-yellow-500' : 'text-red-500'}`} />
          </div>
          <div className={`text-lg font-bold ${passRate >= 80 ? 'text-green-600 dark:text-green-400' : passRate >= 60 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'}`}>
            {passRate.toFixed(1)}%
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {testHistory.filter(t => t.passed).length}/{testHistory.length} runs
          </div>
        </div>

        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-600 dark:text-gray-400">Avg Duration</span>
            <FlaskConical className="w-3.5 h-3.5 text-blue-500" />
          </div>
          <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
            {formatDuration(Math.round(avgDuration))}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Per test run
          </div>
        </div>

        <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-600 dark:text-gray-400">Total Tests</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-purple-500" />
          </div>
          <div className="text-lg font-bold text-purple-600 dark:text-purple-400">
            {totalTests}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Across {testHistory.length} runs
          </div>
        </div>
      </div>

      {/* Recent Test Runs */}
      <div>
        <h4 className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">
          Recent Test Runs
        </h4>
        <div className="space-y-2">
          {testHistory.map((test) => (
            <div
              key={test.id}
              className={`
                p-3 rounded-lg border
                ${test.passed
                  ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                  : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                }
              `}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2 flex-1 min-w-0">
                  {test.passed ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        Issue #{test.issue_number}
                      </span>
                      <span className={`text-xs font-medium ${test.passed ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'}`}>
                        {test.passed ? 'PASSED' : 'FAILED'}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-gray-600 dark:text-gray-400">
                      <span>{test.passed_tests}/{test.total_tests} tests</span>
                      <span>•</span>
                      <span>{formatDuration(test.duration_seconds)}</span>
                      <span>•</span>
                      <span>{formatTimestamp(test.timestamp)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Flakiness Detection (placeholder) */}
      {testHistory.filter(t => !t.passed).length > 0 && (
        <div className="p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300 mb-1">
                Flakiness Detected
              </p>
              <p className="text-xs text-yellow-700 dark:text-yellow-400">
                {testHistory.filter(t => !t.passed).length} of the last {testHistory.length} test runs failed. Consider investigating test stability.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
