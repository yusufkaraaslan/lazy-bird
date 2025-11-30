/**
 * System Status Block
 *
 * Shows overall system health, queue depth, active agents, and uptime
 */

import { useEffect, useState } from 'react';
import { Activity, Clock, Server, AlertCircle } from 'lucide-react';
import { systemApi, queueApi, agentsApi } from '../../lib/api';
import type { BlockProps } from '../../config/blockRegistry';

interface SystemStatusData {
  queueDepth: number;
  activeAgents: number;
  systemHealth: 'healthy' | 'degraded' | 'down';
  uptime: number;
}

export function SystemStatusBlock({}: BlockProps) {
  const [data, setData] = useState<SystemStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const [statusRes, queueRes, agentsRes] = await Promise.all([
        systemApi.getStatus(),
        queueApi.getStats(),
        agentsApi.list(),
      ]);

      const systemStatus = statusRes.data;
      const queueStats = queueRes.data;
      const agents = agentsRes.data.agents || [];

      // Calculate system health
      const servicesHealthy = Object.values(systemStatus.services || {}).every(
        (s: any) => s.status === 'running'
      );
      const resourcesOk =
        systemStatus.resources.cpu_percent < 90 &&
        systemStatus.resources.memory_percent < 90;

      const systemHealth = servicesHealthy && resourcesOk
        ? 'healthy'
        : resourcesOk
        ? 'degraded'
        : 'down';

      setData({
        queueDepth: queueStats.total_tasks || 0,
        activeAgents: agents.filter((a: any) => a.status === 'working').length,
        systemHealth,
        uptime: Math.max(...Object.values(systemStatus.services || {}).map((s: any) => s.uptime_seconds || 0)),
      });
      setError(null);
    } catch (err: any) {
      console.error('Failed to fetch system status:', err);
      setError(err.message || 'Failed to load system status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // Refresh every 5 seconds
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

  if (!data) return null;

  const healthColor =
    data.systemHealth === 'healthy'
      ? 'text-green-500'
      : data.systemHealth === 'degraded'
      ? 'text-yellow-500'
      : 'text-red-500';

  const healthBg =
    data.systemHealth === 'healthy'
      ? 'bg-green-50 dark:bg-green-900/20'
      : data.systemHealth === 'degraded'
      ? 'bg-yellow-50 dark:bg-yellow-900/20'
      : 'bg-red-50 dark:bg-red-900/20';

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {/* Queue Depth */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/20">
          <Server className="w-5 h-5 text-blue-500" />
        </div>
        <div>
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {data.queueDepth}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Queue Depth
          </div>
        </div>
      </div>

      {/* Active Agents */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-purple-50 dark:bg-purple-900/20">
          <Activity className="w-5 h-5 text-purple-500" />
        </div>
        <div>
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {data.activeAgents}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Active Agents
          </div>
        </div>
      </div>

      {/* System Health */}
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${healthBg}`}>
          <AlertCircle className={`w-5 h-5 ${healthColor}`} />
        </div>
        <div>
          <div className={`text-sm font-semibold ${healthColor} capitalize`}>
            {data.systemHealth}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            System Health
          </div>
        </div>
      </div>

      {/* Uptime */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700">
          <Clock className="w-5 h-5 text-gray-600 dark:text-gray-300" />
        </div>
        <div>
          <div className="text-sm font-bold text-gray-900 dark:text-gray-100">
            {formatUptime(data.uptime)}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Uptime
          </div>
        </div>
      </div>
    </div>
  );
}
