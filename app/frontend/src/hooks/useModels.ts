import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { ModelsResponse } from '@/lib/types';

export const useModels = () => {
  const modelsQuery = useQuery({
    queryKey: ['models'],
    queryFn: async () => {
      const response = await api.get<ModelsResponse>('/nlq/models');
      return response.data;
    },
  });

  return {
    models: modelsQuery.data?.models || [],
    isLoading: modelsQuery.isLoading,
    error: modelsQuery.error,
  };
};
