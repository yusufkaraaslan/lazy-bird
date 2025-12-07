/**
 * Project Issues Block
 *
 * Shows all issues for the selected project with filtering and sorting
 */

import { useEffect, useState } from 'react';
import { FileText, Filter, Search, CheckCircle2, Clock, XCircle, AlertTriangle, ArrowUpDown } from 'lucide-react';
import { issuesApi } from '../../lib/api';
import { useDashboardStore } from '../../store';
import type { BlockProps } from '../../config/blockRegistry';
import type { Issue } from '../../types/api';

type StatusFilter = 'all' | 'queued' | 'processing' | 'testing' | 'done' | 'failed';
type ComplexityFilter = 'all' | 'simple' | 'medium' | 'complex';
type SortBy = 'date' | 'status' | 'complexity';

export function ProjectIssuesBlock({}: BlockProps) {
  const selectedProjectId = useDashboardStore((state) => state.selectedProjectId);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [complexityFilter, setComplexityFilter] = useState<ComplexityFilter>('all');
  const [sortBy, setSortBy] = useState<SortBy>('date');
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    const fetchIssues = async () => {
      if (!selectedProjectId) {
        setIssues([]);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const response = await issuesApi.list({ project_id: selectedProjectId });
        setIssues(response.data.issues || []);
        setError(null);
      } catch (err: any) {
        console.error('Failed to fetch issues:', err);
        setError(err.message || 'Failed to load issues');
      } finally {
        setLoading(false);
      }
    };

    fetchIssues();
    const interval = setInterval(fetchIssues, 15000); // Refresh every 15 seconds
    return () => clearInterval(interval);
  }, [selectedProjectId]);

  // Filter and sort issues
  const filteredIssues = issues
    .filter(issue => {
      // Search filter
      if (searchQuery && !issue.title.toLowerCase().includes(searchQuery.toLowerCase())) {
        return false;
      }
      // Status filter
      if (statusFilter !== 'all' && issue.status !== statusFilter) {
        return false;
      }
      // Complexity filter
      if (complexityFilter !== 'all' && issue.complexity !== complexityFilter) {
        return false;
      }
      return true;
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'status':
          return a.status.localeCompare(b.status);
        case 'complexity':
          const complexityOrder = { simple: 1, medium: 2, complex: 3 };
          return (complexityOrder[a.complexity || 'medium'] || 2) - (complexityOrder[b.complexity || 'medium'] || 2);
        case 'date':
        default:
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'done':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'processing':
      case 'testing':
        return <Clock className="w-4 h-4 text-blue-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'queued':
      default:
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'done':
        return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400';
      case 'processing':
      case 'testing':
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400';
      case 'failed':
        return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400';
      case 'queued':
      default:
        return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400';
    }
  };

  const getComplexityBadge = (complexity?: string) => {
    if (!complexity) return null;

    const colors = {
      simple: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300',
      medium: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
      complex: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400',
    };

    return (
      <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[complexity as keyof typeof colors] || colors.medium}`}>
        {complexity}
      </span>
    );
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
        <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No project selected</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with search and filters */}
      <div className="flex items-center justify-between gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search issues..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 dark:text-gray-100"
          />
        </div>

        {/* Filter toggle & sort */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              showFilters
                ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            <Filter className="w-4 h-4" />
            Filters
          </button>

          <button
            onClick={() => {
              const order: SortBy[] = ['date', 'status', 'complexity'];
              const currentIndex = order.indexOf(sortBy);
              setSortBy(order[(currentIndex + 1) % order.length]);
            }}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            title={`Sort by: ${sortBy}`}
          >
            <ArrowUpDown className="w-4 h-4" />
            {sortBy}
          </button>
        </div>
      </div>

      {/* Filter dropdowns */}
      {showFilters && (
        <div className="grid grid-cols-2 gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
          {/* Status filter */}
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              className="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 dark:text-gray-100"
            >
              <option value="all">All Statuses</option>
              <option value="queued">Queued</option>
              <option value="processing">Processing</option>
              <option value="testing">Testing</option>
              <option value="done">Done</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          {/* Complexity filter */}
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Complexity
            </label>
            <select
              value={complexityFilter}
              onChange={(e) => setComplexityFilter(e.target.value as ComplexityFilter)}
              className="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 dark:text-gray-100"
            >
              <option value="all">All Complexities</option>
              <option value="simple">Simple</option>
              <option value="medium">Medium</option>
              <option value="complex">Complex</option>
            </select>
          </div>
        </div>
      )}

      {/* Results count */}
      <div className="text-xs text-gray-500 dark:text-gray-400">
        Showing {filteredIssues.length} of {issues.length} issues
      </div>

      {/* Issues list */}
      {filteredIssues.length === 0 ? (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No issues found</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredIssues.map((issue) => (
            <div
              key={issue.number}
              className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer border border-gray-200 dark:border-gray-600"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  {/* Title and number */}
                  <div className="flex items-start gap-2 mb-2">
                    <span className="text-xs font-mono text-gray-500 dark:text-gray-400">
                      #{issue.number}
                    </span>
                    <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 line-clamp-2">
                      {issue.title}
                    </h4>
                  </div>

                  {/* Meta info */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(issue.status)}`}>
                      {getStatusIcon(issue.status)}
                      {issue.status}
                    </span>
                    {getComplexityBadge(issue.complexity)}
                    {issue.progress !== undefined && issue.progress > 0 && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {issue.progress}% complete
                      </span>
                    )}
                  </div>
                </div>

                {/* Date */}
                <div className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                  {new Date(issue.created_at).toLocaleDateString()}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
