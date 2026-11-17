import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';

export const useCsvExport = (connectionId: string | null) => {
  const exportMutation = useMutation({
    mutationFn: async ({ sql, filename }: { sql: string; filename?: string }) => {
      if (!connectionId) throw new Error('No connection');
      await apiClient.downloadCsv(connectionId, { sql, filename });
    },
  });

  return {
    exportCsv: exportMutation.mutate,
    isExporting: exportMutation.isPending,
    error: exportMutation.error,
  };
};
