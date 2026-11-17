import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { AccountHistoryItem, AccountHistoryResponse } from '@/lib/types';

export const useHistory = (limit = 50) => {
  const historyQuery = useQuery({
    queryKey: ['history', limit],
    queryFn: async () => {
      const response = await api.get<AccountHistoryResponse>(`/account/history?limit=${limit}`);
      return response.data.items;
    },
  });

  return {
    history: historyQuery.data || [],
    isLoading: historyQuery.isLoading,
    error: historyQuery.error,
    refetch: historyQuery.refetch,
  };
};
