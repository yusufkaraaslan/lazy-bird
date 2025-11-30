/**
 * Agent Status Block
 *
 * Shows all agents with their status, current tasks, and resource usage
 */

import { useEffect, useState } from 'react';
import { Bot, Cpu, MemoryStick, Clock, AlertCircle } from 'lucide-react';
import { agentsApi } from '../../lib/api';
import type { BlockProps } from '../../config/blockRegistry';
import type { Agent } from '../../types/api';

export function AgentStatusBlock({}: BlockProps) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const agentsRes = await agentsApi.list();
      setAgents(agentsRes.data.agents || []);
      setError(null);
    } catch (err: any) {
      console.error('Failed to fetch agents:', err);
      setError(err.message || 'Failed to load agents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
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

  if (agents.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <Bot className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No agents running</p>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'working':
        return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20';
      case 'idle':
        return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20';
      case 'error':
        return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20';
      default:
        return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50';
    }
  };

  const formatDuration = (isoDate: string) => {
    const start = new Date(isoDate);
    const now = new Date();
    const diffMs = now.getTime() - start.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 60) return `${diffMins}m`;
    const hours = Math.floor(diffMins / 60);
    if (hours < 24) return `${hours}h ${diffMins % 60}m`;
    const days = Math.floor(hours / 24);
    return `${days}d ${hours % 24}h`;
  };

  return (
    <div className="space-y-3">
      {agents.map((agent) => (
        <div
          key={agent.agent_id}
          className="p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center gap-2">
              <Bot className="w-5 h-5 text-primary-500" />
              <div>
                <div className="font-medium text-sm text-gray-900 dark:text-gray-100">
                  {agent.agent_id}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  PID: {agent.pid}
                </div>
              </div>
            </div>
            <div className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(agent.status)}`}>
              {agent.status}
            </div>
          </div>

          {/* Current task */}
          {agent.current_task && (
            <div className="mb-2 p-2 rounded bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600">
              <div className="text-xs font-medium text-gray-700 dark:text-gray-300">
                Issue #{agent.current_task.issue_number} - {agent.current_task.project_id}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 mt-1">
                <Clock className="w-3 h-3" />
                Started {formatDuration(agent.current_task.started_at)} ago
              </div>
            </div>
          )}

          {/* Resource usage */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-gray-400" />
              <span className="text-gray-600 dark:text-gray-400">
                CPU: <span className="font-medium text-gray-900 dark:text-gray-100">{agent.cpu_percent.toFixed(1)}%</span>
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <MemoryStick className="w-3.5 h-3.5 text-gray-400" />
              <span className="text-gray-600 dark:text-gray-400">
                RAM: <span className="font-medium text-gray-900 dark:text-gray-100">{(agent.memory_mb / 1024).toFixed(1)}GB</span>
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
