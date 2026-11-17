import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { SafeModeResponse } from '@/lib/types';

export const useSafeMode = () => {
  const queryClient = useQueryClient();

  const safeModeQuery = useQuery({
    queryKey: ['safe-mode'],
    queryFn: async () => {
      const response = await api.get<SafeModeResponse>('/settings/safe-mode');
      return response.data;
    },
    staleTime: 30_000,
  });

  const updateMutation = useMutation({
    mutationFn: async (enabled: boolean) => {
      const response = await api.post<SafeModeResponse>('/settings/safe-mode', { enabled });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['safe-mode'], data);
    },
  });

  return {
    safeModeEnabled: safeModeQuery.data?.enabled ?? true,
    isLoading: safeModeQuery.isLoading || updateMutation.isPending,
    error: safeModeQuery.error || updateMutation.error,
    setSafeMode: (enabled: boolean) => updateMutation.mutate(enabled),
    toggleSafeMode: () => updateMutation.mutate(!(safeModeQuery.data?.enabled ?? true)),
    refetchSafeMode: safeModeQuery.refetch,
  };
};
