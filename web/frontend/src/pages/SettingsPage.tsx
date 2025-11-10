/**
 * Settings page - Configuration management
 */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { settingsApi, systemApi } from '../lib/api';
import { AlertCircle, CheckCircle, Key, RefreshCw, Shield, Play, Square, RotateCw, Power, ServerCog } from 'lucide-react';
import { useSystemStatus, useServiceControl } from '../hooks/useSystem';

export function SettingsPage() {
  const [token, setToken] = useState('');
  const [showToken, setShowToken] = useState(false);
  const queryClient = useQueryClient();

  const { data: systemStatus } = useSystemStatus();
  const serviceControl = useServiceControl();

  const { data: tokenStatus, isLoading } = useQuery({
    queryKey: ['settings', 'token'],
    queryFn: async () => {
      const response = await settingsApi.getTokenStatus();
      return response.data;
    },
  });

  const updateToken = useMutation({
    mutationFn: async (newToken: string) => {
      const response = await settingsApi.updateToken(newToken);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', 'token'] });
      setToken('');
      setShowToken(false);
    },
  });

  const testToken = useMutation({
    mutationFn: async () => {
      const response = await settingsApi.testToken();
      return response.data;
    },
  });

  const handleUpdateToken = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token.trim()) return;

    try {
      await updateToken.mutateAsync(token);
    } catch (err) {
      console.error('Failed to update token:', err);
    }
  };

  const handleTestToken = async () => {
    try {
      await testToken.mutateAsync();
    } catch (err) {
      console.error('Failed to test token:', err);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="max-w-4xl mx-auto p-6 lg:p-8">
          <div className="text-gray-600 dark:text-gray-400">Loading settings...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-4xl mx-auto p-6 lg:p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Settings</h1>
          <p className="text-gray-600 dark:text-gray-400">Configure GitHub integration and system settings</p>
        </div>

        {/* GitHub Token Section */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm mb-6">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3 mb-2">
              <Key size={24} className="text-blue-600 dark:text-blue-400" />
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">GitHub Access Token</h2>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Required for the issue-watcher to fetch issues from your repositories
            </p>
          </div>

          <div className="p-6">
            {/* Current Token Status */}
            {tokenStatus?.exists && (
              <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Current Token</span>
                  <button
                    onClick={handleTestToken}
                    disabled={testToken.isPending}
                    className="text-sm text-blue-600 dark:text-blue-400 hover:underline disabled:opacity-50"
                  >
                    {testToken.isPending ? 'Testing...' : 'Test Token'}
                  </button>
                </div>
                <div className="font-mono text-sm text-gray-900 dark:text-white mb-2">
                  {tokenStatus.masked_token}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  Length: {tokenStatus.length} characters
                </div>

                {/* Test Result */}
                {testToken.data && (
                  <div className={`mt-4 p-3 rounded-lg ${
                    testToken.data.valid
                      ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700/50'
                      : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700/50'
                  }`}>
                    <div className="flex items-center gap-2 mb-2">
                      {testToken.data.valid ? (
                        <CheckCircle size={20} className="text-green-600 dark:text-green-400" />
                      ) : (
                        <AlertCircle size={20} className="text-red-600 dark:text-red-400" />
                      )}
                      <span className={`font-medium ${
                        testToken.data.valid
                          ? 'text-green-900 dark:text-green-100'
                          : 'text-red-900 dark:text-red-100'
                      }`}>
                        {testToken.data.valid ? 'Token is valid' : 'Token is invalid'}
                      </span>
                    </div>
                    {testToken.data.valid ? (
                      <div className="text-sm space-y-1">
                        <div className="text-green-800 dark:text-green-200">
                          <span className="font-medium">User:</span> {testToken.data.username}
                          {testToken.data.name && ` (${testToken.data.name})`}
                        </div>
                        <div className="text-green-800 dark:text-green-200">
                          <span className="font-medium">Scopes:</span> {testToken.data.scopes?.join(', ') || 'None'}
                        </div>
                      </div>
                    ) : (
                      <div className="text-sm text-red-800 dark:text-red-200">
                        {testToken.data.error}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Update Token Form */}
            <form onSubmit={handleUpdateToken} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {tokenStatus?.exists ? 'Update Token' : 'Add Token'}
                </label>
                <div className="relative">
                  <input
                    type={showToken ? 'text' : 'password'}
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                    className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setShowToken(!showToken)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                  >
                    {showToken ? 'Hide' : 'Show'}
                  </button>
                </div>
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  GitHub Personal Access Token with <code className="bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded">repo</code> and <code className="bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded">workflow</code> scopes
                </p>
              </div>

              {updateToken.error && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700/50 rounded-lg">
                  <div className="flex items-center gap-2 text-red-800 dark:text-red-200 text-sm">
                    <AlertCircle size={16} />
                    <span>{(updateToken.error as any)?.response?.data?.error || 'Failed to update token'}</span>
                  </div>
                </div>
              )}

              {updateToken.isSuccess && (
                <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700/50 rounded-lg">
                  <div className="flex items-center gap-2 text-green-800 dark:text-green-200 text-sm mb-2">
                    <CheckCircle size={16} />
                    <span>Token updated successfully!</span>
                  </div>
                  <div className="flex items-center gap-2 text-yellow-800 dark:text-yellow-200 text-sm">
                    <RefreshCw size={16} />
                    <span>Restart the issue-watcher service for changes to take effect</span>
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={!token.trim() || updateToken.isPending}
                className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {updateToken.isPending ? 'Updating...' : 'Update Token'}
              </button>
            </form>
          </div>
        </div>

        {/* Service Management Section */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm mb-6">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3 mb-2">
              <ServerCog size={24} className="text-blue-600 dark:text-blue-400" />
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Service Management</h2>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Control systemd services (issue-watcher, agent-runner, etc.)
            </p>
          </div>

          <div className="p-6">
            {systemStatus?.services && Object.entries(systemStatus.services).length > 0 ? (
              <div className="space-y-4">
                {Object.entries(systemStatus.services).map(([name, service]: [string, any]) => (
                  <div key={name} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="font-medium text-gray-900 dark:text-white">{name}</span>
                        {service.status === 'running' ? (
                          <span className="px-2 py-1 text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 rounded-full flex items-center gap-1">
                            <CheckCircle size={12} />
                            Running
                          </span>
                        ) : (
                          <span className="px-2 py-1 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-full flex items-center gap-1">
                            <AlertCircle size={12} />
                            Stopped
                          </span>
                        )}
                      </div>
                      {service.status === 'running' && service.uptime_seconds !== undefined && (
                        <div className="text-sm text-gray-600 dark:text-gray-400">
                          Uptime: {Math.floor(service.uptime_seconds / 3600)}h {Math.floor((service.uptime_seconds % 3600) / 60)}m
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {service.status !== 'running' && (
                        <button
                          onClick={() => serviceControl.mutateAsync({ service: name, action: 'start' })}
                          disabled={serviceControl.isPending}
                          className="px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                          title="Start service"
                        >
                          <Play size={16} />
                          Start
                        </button>
                      )}
                      {service.status === 'running' && (
                        <>
                          <button
                            onClick={() => serviceControl.mutateAsync({ service: name, action: 'stop' })}
                            disabled={serviceControl.isPending}
                            className="px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            title="Stop service"
                          >
                            <Square size={16} />
                            Stop
                          </button>
                          <button
                            onClick={() => serviceControl.mutateAsync({ service: name, action: 'restart' })}
                            disabled={serviceControl.isPending}
                            className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            title="Restart service"
                          >
                            <RotateCw size={16} />
                            Restart
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <Power size={48} className="mx-auto mb-4 opacity-50" />
                <p>No systemd services configured</p>
                <p className="text-sm mt-2">Services will appear here once installed</p>
              </div>
            )}

            {serviceControl.isError && (
              <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700/50 rounded-lg">
                <div className="flex items-center gap-2 text-red-800 dark:text-red-200 text-sm">
                  <AlertCircle size={16} />
                  <span>{(serviceControl.error as any)?.response?.data?.error || 'Service control failed'}</span>
                </div>
              </div>
            )}

            {serviceControl.isSuccess && (
              <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700/50 rounded-lg">
                <div className="flex items-center gap-2 text-green-800 dark:text-green-200 text-sm">
                  <CheckCircle size={16} />
                  <span>Service command executed successfully</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* How to Create Token */}
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-700/50 p-6">
          <div className="flex items-start gap-3 mb-4">
            <Shield size={24} className="text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-2">
                How to Create a GitHub Token
              </h3>
              <ol className="space-y-2 text-sm text-blue-800 dark:text-blue-200">
                <li className="flex gap-2">
                  <span className="font-semibold">1.</span>
                  <span>Go to <a href="https://github.com/settings/tokens/new" target="_blank" rel="noopener noreferrer" className="underline hover:no-underline">GitHub Token Settings</a></span>
                </li>
                <li className="flex gap-2">
                  <span className="font-semibold">2.</span>
                  <span>Give it a name like "Lazy_Bird Issue Watcher"</span>
                </li>
                <li className="flex gap-2">
                  <span className="font-semibold">3.</span>
                  <span>Set expiration (recommend "No expiration" for automation)</span>
                </li>
                <li className="flex gap-2">
                  <span className="font-semibold">4.</span>
                  <span>Select scopes: <code className="bg-blue-100 dark:bg-blue-800 px-1 py-0.5 rounded">repo</code> (full control) and <code className="bg-blue-100 dark:bg-blue-800 px-1 py-0.5 rounded">workflow</code></span>
                </li>
                <li className="flex gap-2">
                  <span className="font-semibold">5.</span>
                  <span>Click "Generate token" and copy it immediately</span>
                </li>
                <li className="flex gap-2">
                  <span className="font-semibold">6.</span>
                  <span>Paste the token in the field above and click "Update Token"</span>
                </li>
              </ol>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
