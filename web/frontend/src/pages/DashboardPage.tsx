/**
 * Dashboard page - System status overview
 */
import { useSystemStatus, useServiceControl } from '../hooks/useSystem';
import { useQueueStats } from '../hooks/useQueue';
import { Play, Square, RotateCw, AlertCircle, CheckCircle, XCircle } from 'lucide-react';

export function DashboardPage() {
  const { data: systemStatus, isLoading, error } = useSystemStatus();
  const { data: queueStats } = useQueueStats();
  const serviceControl = useServiceControl();

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="text-gray-600 dark:text-gray-400">Loading system status...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 p-4 rounded-lg">
          <div className="flex items-center gap-2">
            <AlertCircle size={20} />
            <span>Failed to load system status</span>
          </div>
        </div>
      </div>
    );
  }

  const handleServiceAction = async (service: string, action: 'start' | 'stop' | 'restart') => {
    try {
      await serviceControl.mutateAsync({ service, action });
    } catch (err) {
      console.error('Service control failed:', err);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-green-600 dark:text-green-400';
      case 'stopped':
        return 'text-gray-600 dark:text-gray-400';
      case 'error':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-yellow-600 dark:text-yellow-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <CheckCircle size={20} className="text-green-600 dark:text-green-400" />;
      case 'stopped':
        return <Square size={20} className="text-gray-600 dark:text-gray-400" />;
      default:
        return <XCircle size={20} className="text-red-600 dark:text-red-400" />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto p-6 lg:p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400">System status and service management</p>
        </div>

        {/* System Resources */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">System Resources</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* CPU */}
            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
              <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">CPU Usage</div>
              <div className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
                {systemStatus?.resources.cpu_percent.toFixed(1)}%
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                <div
                  className="bg-blue-600 h-3 rounded-full transition-all duration-300"
                  style={{ width: `${systemStatus?.resources.cpu_percent}%` }}
                />
              </div>
            </div>

            {/* Memory */}
            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
              <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">Memory Usage</div>
              <div className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
                {systemStatus?.resources.memory_percent.toFixed(1)}%
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                {systemStatus?.resources.memory_used_gb.toFixed(1)} GB / {systemStatus?.resources.memory_total_gb.toFixed(1)} GB
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                <div
                  className="bg-green-600 h-3 rounded-full transition-all duration-300"
                  style={{ width: `${systemStatus?.resources.memory_percent}%` }}
                />
              </div>
            </div>

            {/* Disk */}
            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
              <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-3">Disk Usage</div>
              <div className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
                {systemStatus?.resources.disk_percent.toFixed(1)}%
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                {systemStatus?.resources.disk_free_gb.toFixed(1)} GB free / {systemStatus?.resources.disk_total_gb.toFixed(1)} GB total
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                <div
                  className="bg-purple-600 h-3 rounded-full transition-all duration-300"
                  style={{ width: `${systemStatus?.resources.disk_percent}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Services */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">Services</h2>
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900/50">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                    Service
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                    Uptime
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700/50">
              {systemStatus && Object.entries(systemStatus.services).map(([name, service]) => (
                <tr key={name}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(service.status)}
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        {name}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`text-sm font-medium ${getStatusColor(service.status)}`}>
                      {service.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                    {service.uptime_seconds > 0
                      ? `${Math.floor(service.uptime_seconds / 3600)}h ${Math.floor((service.uptime_seconds % 3600) / 60)}m`
                      : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => handleServiceAction(name, 'start')}
                        disabled={service.status === 'running' || serviceControl.isPending}
                        className="p-2 text-green-600 hover:bg-green-50 dark:hover:bg-green-900 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Start"
                      >
                        <Play size={16} />
                      </button>
                      <button
                        onClick={() => handleServiceAction(name, 'stop')}
                        disabled={service.status === 'stopped' || serviceControl.isPending}
                        className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Stop"
                      >
                        <Square size={16} />
                      </button>
                      <button
                        onClick={() => handleServiceAction(name, 'restart')}
                        disabled={serviceControl.isPending}
                        className="p-2 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Restart"
                      >
                        <RotateCw size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

        {/* Configuration & Queue Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Config */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Configuration</h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center py-2">
                <span className="text-sm text-gray-600 dark:text-gray-400">Phase:</span>
                <span className="font-semibold text-lg text-gray-900 dark:text-white">{systemStatus?.config.phase}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-t border-gray-100 dark:border-gray-700">
                <span className="text-sm text-gray-600 dark:text-gray-400">Projects:</span>
                <span className="font-semibold text-lg text-gray-900 dark:text-white">{systemStatus?.config.projects_count}</span>
              </div>
            </div>
          </div>

          {/* Queue Stats */}
          {queueStats && (
            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Queue Statistics</h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center py-2">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Total Tasks:</span>
                  <span className="font-semibold text-lg text-gray-900 dark:text-white">{queueStats.total_tasks}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-t border-gray-100 dark:border-gray-700">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Simple:</span>
                  <span className="font-semibold text-lg text-green-600 dark:text-green-400">{queueStats.by_complexity.simple}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-t border-gray-100 dark:border-gray-700">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Medium:</span>
                  <span className="font-semibold text-lg text-yellow-600 dark:text-yellow-400">{queueStats.by_complexity.medium}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-t border-gray-100 dark:border-gray-700">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Complex:</span>
                  <span className="font-semibold text-lg text-red-600 dark:text-red-400">{queueStats.by_complexity.complex}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
