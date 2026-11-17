import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { NLQRunPayload, NLQRunResult, NLQExplainResult } from '@/lib/types';

export const useNLQ = (connectionId: string | null) => {
  const runMutation = useMutation({
    mutationFn: async (payload: NLQRunPayload) => {
      if (!connectionId) throw new Error('No connection');
      const response = await api.post<NLQRunResult>(
        `/nlq/${connectionId}`,
        payload
      );
      return response.data;
    },
  });

  const explainMutation = useMutation({
    mutationFn: async (payload: NLQRunPayload) => {
      if (!connectionId) throw new Error('No connection');
      const response = await api.post<NLQExplainResult>(
        `/nlq/explain/${connectionId}`,
        payload
      );
      return response.data;
    },
  });

  return {
    run: runMutation.mutate,
    runAsync: runMutation.mutateAsync,
    explain: explainMutation.mutate,
    explainAsync: explainMutation.mutateAsync,
    runResult: runMutation.data,
    explainResult: explainMutation.data,
    isRunning: runMutation.isPending,
    isExplaining: explainMutation.isPending,
    runError: runMutation.error,
    explainError: explainMutation.error,
    reset: () => {
      runMutation.reset();
      explainMutation.reset();
    },
  };
};
