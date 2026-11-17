import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, apiClient } from '@/lib/api';
import { TokenResponse, UserProfile } from '@/lib/types';

const TOKEN_KEY = 'nl_sql_token';
const REFRESH_KEY = 'nl_sql_refresh';

interface AuthContextValue {
  user: UserProfile | null;
  accessToken: string | null;
  refreshToken: string | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (payload: { username: string; email?: string; full_name?: string; password: string }) => Promise<void>;
  logout: () => void;
  refetchProfile: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const queryClient = useQueryClient();
  const [accessToken, setAccessToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [refreshToken, setRefreshToken] = useState<string | null>(() => localStorage.getItem(REFRESH_KEY));
  const fetchProfile = async () => {
    const res = await api.get<UserProfile>('/auth/me');
    return res.data;
  };

  useEffect(() => {
    apiClient.setAccessToken(accessToken);
    if (accessToken) {
      localStorage.setItem(TOKEN_KEY, accessToken);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
    if (refreshToken) {
      localStorage.setItem(REFRESH_KEY, refreshToken);
    } else {
      localStorage.removeItem(REFRESH_KEY);
    }
  }, [accessToken, refreshToken]);

  const profileQuery = useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      if (!accessToken) return null;
      return fetchProfile();
    },
    enabled: !!accessToken,
    staleTime: 5 * 60 * 1000,
  });

  const handleAuthSuccess = (data: TokenResponse) => {
    setAccessToken(data.access_token);
    apiClient.setAccessToken(data.access_token);
    setRefreshToken(data.refresh_token);
  };

  const loginMutation = useMutation({
    mutationFn: async (payload: { username: string; password: string }) => {
      const form = new URLSearchParams();
      form.append('username', payload.username);
      form.append('password', payload.password);
      const res = await api.post<TokenResponse>('/auth/login', form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      return res.data;
    },
    onSuccess: handleAuthSuccess,
  });

  const registerMutation = useMutation({
    mutationFn: async (payload: { username: string; email?: string; full_name?: string; password: string }) => {
      await api.post('/auth/register', payload);
      // Auto-login after register
      const form = new URLSearchParams();
      form.append('username', payload.username);
      form.append('password', payload.password);
      const res = await api.post<TokenResponse>('/auth/login', form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      return res.data;
    },
    onSuccess: handleAuthSuccess,
  });

  const logout = () => {
    setAccessToken(null);
    setRefreshToken(null);
    queryClient.removeQueries({ queryKey: ['me'] });
    // Force navigation to login after clearing state
    if (typeof window !== 'undefined') {
      window.location.replace('/login');
    }
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      user: profileQuery.data || null,
      accessToken,
      refreshToken,
      isLoading: profileQuery.isLoading || loginMutation.isPending || registerMutation.isPending,
      login: async (u, p) => {
        const res = await loginMutation.mutateAsync({ username: u, password: p });
        handleAuthSuccess(res);
        const profile = await fetchProfile();
        queryClient.setQueryData(['me'], profile);
      },
      register: async (payload) => {
        const res = await registerMutation.mutateAsync(payload);
        handleAuthSuccess(res);
        const profile = await fetchProfile();
        queryClient.setQueryData(['me'], profile);
      },
      logout,
      refetchProfile: () => profileQuery.refetch(),
    }),
    [profileQuery.data, profileQuery.isLoading, loginMutation.isPending, registerMutation.isPending, accessToken, refreshToken]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
