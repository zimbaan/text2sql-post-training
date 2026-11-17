import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, apiClient } from '@/lib/api';
import { ConnectPayload, ConnectResponse } from '@/lib/types';
import React, { useEffect, useState, useRef, createContext, useContext, ReactNode } from 'react';

const CONNECTION_STORAGE_KEY = 'sql_agent_connection';

interface ConnectionContextValue {
  connectionId: string | null;
  connection: ConnectResponse | null | undefined;
  isConnected: boolean;
  isConnecting: boolean;
  connect: (payload: ConnectPayload, options?: any) => void;
  disconnect: () => void;
  clearStaleConnection: () => void;
  error: any;
}

const ConnectionContext = createContext<ConnectionContextValue | undefined>(undefined);

const useProvideConnection = (): ConnectionContextValue => {
  const queryClient = useQueryClient();
  const [connectionId, setConnectionId] = useState<string | null>(() => {
    return localStorage.getItem(CONNECTION_STORAGE_KEY);
  });
  const validationRef = useRef(false); // Track if we've already validated

  useEffect(() => {
    if (connectionId) {
      localStorage.setItem(CONNECTION_STORAGE_KEY, connectionId);
      apiClient.setConnectionId(connectionId);
    } else {
      localStorage.removeItem(CONNECTION_STORAGE_KEY);
      apiClient.setConnectionId(null);
    }
  }, [connectionId]);

  const connectMutation = useMutation({
    mutationFn: async (payload: ConnectPayload) => {
      const response = await api.post<ConnectResponse>('/connect', payload);
      return response.data;
    },
    onSuccess: (data) => {
      setConnectionId(data.connection_id);
      // Cache the connection data so it's available immediately
      queryClient.setQueryData(['connection', data.connection_id], data);
      queryClient.invalidateQueries({ queryKey: ['connection'] });
      // Invalidate schemas to trigger reload
      queryClient.invalidateQueries({ queryKey: ['schemas'] });
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: async (connId: string) => {
      try {
        await api.delete(`/connect/${connId}`);
      } catch (error: any) {
        // If connection already doesn't exist (404), that's fine
        // We'll clear the local state anyway
        if (error.response?.status === 404) {
          // Connection doesn't exist on server, which is fine
          return;
        }
        throw error;
      }
    },
    onSuccess: () => {
      // Always clear local state on success
      setConnectionId(null);
      queryClient.clear();
    },
    onError: (error: any) => {
      // Always clear local state on any error (connection not found, etc.)
      // This handles stale connections after server restart
      setConnectionId(null);
      queryClient.clear();
    },
  });

  // Clear connection if schemas query fails with 404 (stale connection)
  const clearStaleConnection = () => {
    console.log('clearStaleConnection called, clearing connectionId:', connectionId);
    setConnectionId(null);
    queryClient.clear();
  };

  const connectionQuery = useQuery({
    queryKey: ['connection', connectionId],
    queryFn: async () => {
      if (!connectionId) return null;
      // Try to get from cache first
      const cached = queryClient.getQueryData<ConnectResponse>(['connection', connectionId]);
      if (cached) return cached;
      // If not cached and we have connectionId from localStorage, 
      // return a minimal connection object to keep UI working
      // In a real app, you might have a GET /connect/{id} endpoint
      return null;
    },
    enabled: !!connectionId,
    staleTime: Infinity, // Connection data doesn't change unless we reconnect
  });

  // Get connection data from cache or mutation result
  const connection = connectionQuery.data || connectMutation.data;

  // Validate connection immediately on mount if connectionId exists
  useEffect(() => {
    if (!connectionId || validationRef.current) return;
    validationRef.current = true; // Mark as validated to prevent duplicate runs
    
    // Immediately try to validate the connection by fetching schemas
    // This will detect stale connections right away
    const validateConnection = async () => {
      try {
        await api.get(`/schemas/${connectionId}`);
        console.log('Connection validated successfully on mount:', connectionId);
      } catch (error: any) {
        if (error?.response?.status === 404) {
          console.log('Stale connection detected on mount, clearing:', connectionId);
          // Clear immediately
          setConnectionId(null);
          queryClient.clear();
          // Also clear from localStorage immediately
          localStorage.removeItem(CONNECTION_STORAGE_KEY);
          apiClient.setConnectionId(null);
        }
      }
    };
    
    // Small delay to avoid race conditions, but validate immediately
    const timeoutId = setTimeout(validateConnection, 50);
    return () => clearTimeout(timeoutId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on mount
  
  // Reset validation ref when connectionId changes (new connection)
  useEffect(() => {
    if (connectionId) {
      validationRef.current = false;
    }
  }, [connectionId]);

  return {
    connectionId,
    connection,
    isConnected: !!connectionId,
    isConnecting: connectMutation.isPending,
    connect: connectMutation.mutate,
    disconnect: () => {
      if (connectionId) {
        disconnectMutation.mutate(connectionId);
      }
    },
    clearStaleConnection,
    error: connectMutation.error || disconnectMutation.error,
  };
};

export const ConnectionProvider = ({ children }: { children: ReactNode }) => {
  const value = useProvideConnection();
  // Use createElement to avoid JSX in this .ts file.
  return React.createElement(ConnectionContext.Provider, { value }, children);
};

export const useConnection = () => {
  const context = useContext(ConnectionContext);
  if (!context) {
    throw new Error('useConnection must be used within a ConnectionProvider');
  }
  return context;
};
