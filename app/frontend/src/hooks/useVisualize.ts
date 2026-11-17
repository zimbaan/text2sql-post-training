import { useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { VisualizePayload, VisualGraph } from '@/lib/types';

export const useVisualize = (connectionId: string | null) => {
  const visualizeMutation = useMutation({
    mutationFn: async (payload: VisualizePayload) => {
      if (!connectionId) throw new Error('No connection');
      const response = await api.post<VisualGraph>(
        `/visualize/${connectionId}`,
        payload
      );
      return response.data;
    },
  });

  return {
    visualize: visualizeMutation.mutate,
    visualizeAsync: visualizeMutation.mutateAsync,
    graph: visualizeMutation.data,
    isLoading: visualizeMutation.isPending,
    error: visualizeMutation.error,
  };
};
