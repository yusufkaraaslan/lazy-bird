/**
 * React Query hooks for system status
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { systemApi } from '../lib/api';
import type { SystemStatus } from '../types/api';

export function useSystemStatus() {
  return useQuery({
    queryKey: ['system', 'status'],
    queryFn: async () => {
      const response = await systemApi.getStatus();
      return response.data as SystemStatus;
    },
    refetchInterval: 5000, // Refetch every 5 seconds
  });
}

export function useServiceControl() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      service,
      action,
    }: {
      service: string;
      action: 'start' | 'stop' | 'restart';
    }) => {
      if (action === 'start') {
        await systemApi.startService(service);
      } else if (action === 'stop') {
        await systemApi.stopService(service);
      } else if (action === 'restart') {
        await systemApi.restartService(service);
      }
    },
    onSuccess: () => {
      // Refetch system status after service control
      queryClient.invalidateQueries({ queryKey: ['system', 'status'] });
    },
  });
}
