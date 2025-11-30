/**
 * API Client for Lazy_Bird Backend
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Projects API
export const projectsApi = {
  list: () => api.get('/api/projects'),
  get: (id: string) => api.get(`/api/projects/${id}`),
  create: (data: any) => api.post('/api/projects', data),
  update: (id: string, data: any) => api.put(`/api/projects/${id}`, data),
  delete: (id: string) => api.delete(`/api/projects/${id}`),
  enable: (id: string) => api.post(`/api/projects/${id}/enable`),
  disable: (id: string) => api.post(`/api/projects/${id}/disable`),
};

// System API
export const systemApi = {
  getStatus: () => api.get('/api/system/status'),
  getServiceStatus: (name: string) => api.get(`/api/system/services/${name}`),
  startService: (name: string) => api.post(`/api/system/services/${name}/start`),
  stopService: (name: string) => api.post(`/api/system/services/${name}/stop`),
  restartService: (name: string) => api.post(`/api/system/services/${name}/restart`),
  getConfig: () => api.get('/api/system/config'),
  updateConfig: (data: any) => api.put('/api/system/config', data),
  // Service file management
  get: (path: string) => api.get(path),
  post: (path: string, data?: any) => api.post(path, data),
  put: (path: string, data?: any) => api.put(path, data),
  delete: (path: string) => api.delete(path),
};

// Queue API
export const queueApi = {
  list: (projectId?: string) =>
    api.get('/api/queue', { params: { project_id: projectId } }),
  get: (id: string) => api.get(`/api/queue/${id}`),
  cancel: (id: string) => api.delete(`/api/queue/${id}`),
  getStats: () => api.get('/api/queue/stats'),
};

// Settings API
export const settingsApi = {
  getTokenStatus: () => api.get('/api/settings/token'),
  updateToken: (token: string) => api.put('/api/settings/token', { token }),
  testToken: () => api.post('/api/settings/token/test'),
};

// Issues API
export const issuesApi = {
  list: (params?: {
    project_id?: string;
    status?: string;
    complexity?: string;
    limit?: number;
    offset?: number;
  }) => api.get('/api/issues', { params }),
  get: (number: number, projectId?: string) =>
    api.get(`/api/issues/${number}`, { params: { project_id: projectId } }),
  getLogs: (number: number, projectId?: string) =>
    api.get(`/api/issues/${number}/logs`, { params: { project_id: projectId } }),
  retry: (number: number, projectId?: string) =>
    api.post(`/api/issues/${number}/retry`, { project_id: projectId }),
  cancel: (number: number, projectId?: string) =>
    api.post(`/api/issues/${number}/cancel`, { project_id: projectId }),
};

// Agents API
export const agentsApi = {
  list: () => api.get('/api/agents'),
  get: (id: string) => api.get(`/api/agents/${id}`),
  getStatus: (id: string) => api.get(`/api/agents/${id}/status`),
  stop: (id: string, force?: boolean) =>
    api.post(`/api/agents/${id}/stop`, { force }),
};

// Analytics API
export const analyticsApi = {
  getOverall: (range?: string) =>
    api.get('/api/analytics/overall', { params: { range } }),
  getProject: (projectId: string, range?: string) =>
    api.get(`/api/analytics/project/${projectId}`, { params: { range } }),
  getCosts: () => api.get('/api/analytics/costs'),
};
