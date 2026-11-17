import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { SchemasResponse, TableInfo } from '@/lib/types';
import { useEffect, useRef } from 'react';

export const useSchemas = (connectionId: string | null, onConnectionLost?: () => void) => {
  // Use a ref to track if we've already called onConnectionLost for this error
  const clearedConnectionRef = useRef<string | null>(null);
  
  const schemasQuery = useQuery({
    queryKey: ['schemas', connectionId],
    queryFn: async () => {
      if (!connectionId) throw new Error('No connection');
      const response = await api.get<SchemasResponse>(`/schemas/${connectionId}`);
      return response.data;
    },
    enabled: !!connectionId,
    retry: (failureCount, error: any) => {
      // Don't retry on 404 (connection not found)
      if (error?.response?.status === 404) return false;
      return failureCount < 2;
    },
  });

  // Reset cleared ref when connectionId changes
  useEffect(() => {
    clearedConnectionRef.current = null;
  }, [connectionId]);
  
  // Also watch for errors in case onError doesn't fire
  useEffect(() => {
    const error = schemasQuery.error as any;
    if (error?.response?.status === 404 && onConnectionLost && connectionId) {
      // Only clear once per connectionId
      if (clearedConnectionRef.current !== connectionId) {
        console.log('useEffect: Clearing stale connection due to 404:', connectionId);
        clearedConnectionRef.current = connectionId;
        onConnectionLost();
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [schemasQuery.error, connectionId]);

  const getTablesDetail = async (tables: string[]) => {
    if (!connectionId) throw new Error('No connection');
    const response = await api.get<{ tables: TableInfo[] }>(
      `/schemas/${connectionId}/tables`,
      {
        params: { tables: tables.join(',') },
      }
    );
    return response.data;
  };

  return {
    schemas: schemasQuery.data,
    isLoading: schemasQuery.isLoading,
    error: schemasQuery.error,
    refetch: schemasQuery.refetch,
    getTablesDetail,
  };
};
