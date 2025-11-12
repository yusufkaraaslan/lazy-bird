/**
 * Service form page for creating/editing systemd services
 */
import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, AlertCircle } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { systemApi } from '../lib/api';

const SERVICE_TEMPLATE = `[Unit]
Description=My Custom Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/working/directory
ExecStart=/usr/bin/python3 /path/to/script.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target`;

export function ServiceFormPage() {
  const navigate = useNavigate();
  const { name } = useParams<{ name: string }>();
  const isEditing = !!name;
  const queryClient = useQueryClient();

  const [serviceName, setServiceName] = useState(name || '');
  const [serviceContent, setServiceContent] = useState(SERVICE_TEMPLATE);
  const [isLoading, setIsLoading] = useState(false);

  // Load service content when editing
  useEffect(() => {
    if (isEditing && name) {
      setIsLoading(true);
      systemApi.get(`/api/system/services/${name}/file`)
        .then(response => {
          setServiceContent(response.data.content);
          setIsLoading(false);
        })
        .catch(err => {
          console.error('Failed to load service:', err);
          setIsLoading(false);
        });
    }
  }, [isEditing, name]);

  // Create service mutation
  const createService = useMutation({
    mutationFn: async (data: { name: string; content: string }) => {
      const response = await systemApi.post('/api/system/services', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['services'] });
      queryClient.invalidateQueries({ queryKey: ['system', 'status'] });
      navigate('/services');
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
      navigate('/services');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isEditing && name) {
      updateService.mutate({ name, content: serviceContent });
    } else {
      if (!serviceName.trim()) return;
      createService.mutate({ name: serviceName, content: serviceContent });
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-full bg-gray-50 dark:bg-gray-900">
        <div className="max-w-4xl mx-auto py-8 px-4">
          <div className="text-gray-600 dark:text-gray-400">Loading service...</div>
        </div>
      </div>
    );
  }

  const error = createService.error || updateService.error;
  const isPending = createService.isPending || updateService.isPending;

  return (
    <div className="min-h-full bg-gray-50 dark:bg-gray-900">
      <div className="max-w-4xl mx-auto py-8 px-4">
        {/* Back button */}
        <button
          onClick={() => navigate('/services')}
          className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-6 transition-colors"
        >
          <ArrowLeft size={20} />
          <span>Back to Services</span>
        </button>

        {/* Page header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {isEditing ? `Edit Service: ${name}` : 'Create New Service'}
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            {isEditing ? 'Update the systemd service configuration' : 'Create a new systemd user service'}
          </p>
        </div>

        {/* Form card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {error && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700/50 rounded-lg">
                <div className="flex items-center gap-2 text-red-800 dark:text-red-200 text-sm">
                  <AlertCircle size={16} />
                  <span>{(error as any)?.response?.data?.error || 'Operation failed'}</span>
                </div>
              </div>
            )}

            {!isEditing && (
              <div>
                <label htmlFor="serviceName" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Service Name
                </label>
                <input
                  type="text"
                  id="serviceName"
                  value={serviceName}
                  onChange={(e) => setServiceName(e.target.value)}
                  placeholder="my-custom-service"
                  required
                  className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono"
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Without .service extension
                </p>
              </div>
            )}

            <div>
              <label htmlFor="serviceContent" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Service File Content
              </label>
              <textarea
                id="serviceContent"
                value={serviceContent}
                onChange={(e) => setServiceContent(e.target.value)}
                rows={20}
                required
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono"
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                systemd service unit configuration
              </p>
            </div>

            {/* Buttons */}
            <div className="flex justify-end gap-2 pt-4 mt-2">
              <button
                type="button"
                onClick={() => navigate('/services')}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isPending || (!serviceName.trim() && !isEditing) || !serviceContent.trim()}
                className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isPending ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Service'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
