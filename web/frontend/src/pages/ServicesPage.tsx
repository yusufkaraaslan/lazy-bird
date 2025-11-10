/**
 * Services page - Full systemd service management
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { systemApi } from '../lib/api';
import { AlertCircle, CheckCircle, Play, Square, RotateCw, Edit, Trash2, Plus, X, Power, FileText, ToggleLeft, ToggleRight } from 'lucide-react';
import { useServiceControl } from '../hooks/useSystem';

interface Service {
  name: string;
  filename: string;
  path: string;
  enabled: boolean;
  status?: string;
}

export function ServicesPage() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [serviceName, setServiceName] = useState('');
  const [serviceContent, setServiceContent] = useState('');

  const queryClient = useQueryClient();
  const serviceControl = useServiceControl();

  // Fetch all services
  const { data: servicesData } = useQuery({
    queryKey: ['services'],
    queryFn: async () => {
      const response = await systemApi.get('/api/system/services');
      return response.data;
    },
    refetchInterval: 5000,
  });

  // Fetch service statuses
  const { data: systemStatus } = useQuery({
    queryKey: ['system', 'status'],
    queryFn: async () => {
      const response = await systemApi.get('/api/system/status');
      return response.data;
    },
    refetchInterval: 5000,
  });

  // Create service mutation
  const createService = useMutation({
    mutationFn: async (data: { name: string; content: string }) => {
      const response = await systemApi.post('/api/system/services', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['services'] });
      queryClient.invalidateQueries({ queryKey: ['system', 'status'] });
      setShowCreateModal(false);
      setServiceName('');
      setServiceContent('');
    },
  });

  // Update service mutation
  const updateService = useMutation({
    mutationFn: async (data: { name: string; content: string }) => {
      const response = await systemApi.put(`/api/system/services/${data.name}`, {
        content: data.content,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['services'] });
      queryClient.invalidateQueries({ queryKey: ['system', 'status'] });
      setShowEditModal(false);
      setSelectedService(null);
      setServiceContent('');
    },
  });

  // Delete service mutation
  const deleteService = useMutation({
    mutationFn: async (name: string) => {
      const response = await systemApi.delete(`/api/system/services/${name}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['services'] });
      queryClient.invalidateQueries({ queryKey: ['system', 'status'] });
    },
  });

  // Enable/disable service
  const toggleServiceEnabled = useMutation({
    mutationFn: async (data: { name: string; enable: boolean }) => {
      const endpoint = data.enable ? 'enable' : 'disable';
      const response = await systemApi.post(`/api/system/services/${data.name}/${endpoint}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['services'] });
    },
  });

  const handleCreateService = () => {
    if (!serviceName.trim() || !serviceContent.trim()) return;
    createService.mutate({ name: serviceName, content: serviceContent });
  };

  const handleEditService = async (serviceName: string) => {
    try {
      const response = await systemApi.get(`/api/system/services/${serviceName}/file`);
      setSelectedService(serviceName);
      setServiceContent(response.data.content);
      setShowEditModal(true);
    } catch (err) {
      console.error('Failed to load service file:', err);
    }
  };

  const handleUpdateService = () => {
    if (!selectedService || !serviceContent.trim()) return;
    updateService.mutate({ name: selectedService, content: serviceContent });
  };

  const handleDeleteService = (serviceName: string) => {
    if (confirm(`Are you sure you want to delete service "${serviceName}"? This will stop and disable the service.`)) {
      deleteService.mutate(serviceName);
    }
  };

  const services = servicesData?.services || [];

  // Template for new service
  const serviceTemplate = `[Unit]
Description=My Custom Service
After=network.target

[Service]
Type=simple
User=${process.env.USER || 'user'}
WorkingDirectory=/path/to/working/directory
ExecStart=/usr/bin/python3 /path/to/script.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target`;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto p-6 lg:p-8">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Services</h1>
            <p className="text-gray-600 dark:text-gray-400">Manage systemd user services</p>
          </div>
          <button
            onClick={() => {
              setServiceName('');
              setServiceContent(serviceTemplate);
              setShowCreateModal(true);
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2 shadow-sm hover:shadow-md"
          >
            <Plus size={20} />
            Create New Service
          </button>
        </div>

        {/* Services List */}
        <div className="space-y-4">
          {services.length === 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-12 text-center">
              <Power size={48} className="mx-auto mb-4 text-gray-400" />
              <p className="text-gray-600 dark:text-gray-400 mb-4">No services found</p>
              <button
                onClick={() => {
                  setServiceName('');
                  setServiceContent(serviceTemplate);
                  setShowCreateModal(true);
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors inline-flex items-center gap-2"
              >
                <Plus size={16} />
                Create Your First Service
              </button>
            </div>
          ) : (
            services.map((service: Service) => {
              const status = systemStatus?.services?.[service.name];
              const isRunning = status?.status === 'running';

              return (
                <div
                  key={service.name}
                  className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                          {service.name}
                        </h3>
                        {isRunning ? (
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
                        <button
                          onClick={() => toggleServiceEnabled.mutate({ name: service.name, enable: !service.enabled })}
                          disabled={toggleServiceEnabled.isPending}
                          className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors disabled:opacity-50"
                          title={service.enabled ? 'Disable auto-start' : 'Enable auto-start'}
                        >
                          {service.enabled ? (
                            <ToggleRight size={20} className="text-blue-600 dark:text-blue-400" />
                          ) : (
                            <ToggleLeft size={20} />
                          )}
                        </button>
                        {service.enabled && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">Auto-start enabled</span>
                        )}
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                        <div className="flex items-center gap-2">
                          <FileText size={14} />
                          <code className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                            {service.path}
                          </code>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 ml-4">
                      {/* Control buttons */}
                      {!isRunning && (
                        <button
                          onClick={() => serviceControl.mutateAsync({ service: service.name, action: 'start' })}
                          disabled={serviceControl.isPending}
                          className="px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                          title="Start service"
                        >
                          <Play size={16} />
                          Start
                        </button>
                      )}
                      {isRunning && (
                        <>
                          <button
                            onClick={() => serviceControl.mutateAsync({ service: service.name, action: 'stop' })}
                            disabled={serviceControl.isPending}
                            className="px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                            title="Stop service"
                          >
                            <Square size={16} />
                            Stop
                          </button>
                          <button
                            onClick={() => serviceControl.mutateAsync({ service: service.name, action: 'restart' })}
                            disabled={serviceControl.isPending}
                            className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                            title="Restart service"
                          >
                            <RotateCw size={16} />
                            Restart
                          </button>
                        </>
                      )}

                      {/* Edit/Delete buttons */}
                      <button
                        onClick={() => handleEditService(service.name)}
                        className="px-3 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors flex items-center gap-2"
                        title="Edit service file"
                      >
                        <Edit size={16} />
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteService(service.name)}
                        className="px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
                        title="Delete service"
                      >
                        <Trash2 size={16} />
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Create Service Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white dark:bg-gray-800 rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Create New Service</h2>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                >
                  <X size={24} />
                </button>
              </div>

              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Service Name (without .service extension)
                  </label>
                  <input
                    type="text"
                    value={serviceName}
                    onChange={(e) => setServiceName(e.target.value)}
                    placeholder="my-custom-service"
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Service File Content
                  </label>
                  <textarea
                    value={serviceContent}
                    onChange={(e) => setServiceContent(e.target.value)}
                    rows={20}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm"
                  />
                </div>

                {createService.isError && (
                  <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700/50 rounded-lg">
                    <div className="flex items-center gap-2 text-red-800 dark:text-red-200 text-sm">
                      <AlertCircle size={16} />
                      <span>{(createService.error as any)?.response?.data?.error || 'Failed to create service'}</span>
                    </div>
                  </div>
                )}

                <div className="flex justify-end gap-3">
                  <button
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleCreateService}
                    disabled={!serviceName.trim() || !serviceContent.trim() || createService.isPending}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {createService.isPending ? 'Creating...' : 'Create Service'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Edit Service Modal */}
        {showEditModal && selectedService && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white dark:bg-gray-800 rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Edit Service: {selectedService}</h2>
                <button
                  onClick={() => {
                    setShowEditModal(false);
                    setSelectedService(null);
                    setServiceContent('');
                  }}
                  className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                >
                  <X size={24} />
                </button>
              </div>

              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Service File Content
                  </label>
                  <textarea
                    value={serviceContent}
                    onChange={(e) => setServiceContent(e.target.value)}
                    rows={20}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm"
                  />
                </div>

                {updateService.isError && (
                  <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700/50 rounded-lg">
                    <div className="flex items-center gap-2 text-red-800 dark:text-red-200 text-sm">
                      <AlertCircle size={16} />
                      <span>{(updateService.error as any)?.response?.data?.error || 'Failed to update service'}</span>
                    </div>
                  </div>
                )}

                <div className="flex justify-end gap-3">
                  <button
                    onClick={() => {
                      setShowEditModal(false);
                      setSelectedService(null);
                      setServiceContent('');
                    }}
                    className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleUpdateService}
                    disabled={!serviceContent.trim() || updateService.isPending}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {updateService.isPending ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
