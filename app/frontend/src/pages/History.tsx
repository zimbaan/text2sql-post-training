import { HistoryPanel } from '@/features/history/HistoryPanel';
import { EmptyState } from '@/components/common/EmptyState';
import { History as HistoryIcon } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';

export const History = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const handleRerun = (query: string) => {
    localStorage.setItem('last_nlq_query', query);
    navigate('/playground');
  };

  const handleLoadToPlayground = (query: string) => {
    localStorage.setItem('last_nlq_query', query);
    navigate('/playground');
  };

  if (!user) {
    return (
      <div className="min-h-screen">
        <div className="container mx-auto py-16">
          <EmptyState
            icon={HistoryIcon}
            title="Sign in to view history"
            description="Your query history is available after you log in."
            action={{
              label: 'Go to Login',
              onClick: () => navigate('/login'),
            }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="container mx-auto py-8 space-y-6">
        <div>
          <h1 className="text-4xl font-bold mb-2 text-slate-50">Query History</h1>
          <p className="text-slate-200">
            Review and re-run your previous natural language queries
          </p>
        </div>

        <HistoryPanel
          onRerun={handleRerun}
          onLoadToPlayground={handleLoadToPlayground}
        />
      </div>
    </div>
  );
};
