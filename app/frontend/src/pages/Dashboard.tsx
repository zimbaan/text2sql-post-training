import { Database, Activity, Shield, Sparkles } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useConnection } from '@/hooks/useConnection';
import { useSchemas } from '@/hooks/useSchemas';
import { useModels } from '@/hooks/useModels';
import { useSafeMode } from '@/hooks/useSafeMode';
import { EmptyState } from '@/components/common/EmptyState';
import { useNavigate } from 'react-router-dom';

const EXAMPLE_QUERIES = [
  'Show me all orders from the last 7 days',
  'What are my top 5 customers by total spend?',
  'Count active users grouped by signup month',
  'Find products with low inventory levels',
  'Calculate average order value by category',
];

export const Dashboard = () => {
  const navigate = useNavigate();
  const { isConnected, connection } = useConnection();
  const { schemas } = useSchemas(connection?.connection_id || null);
  const { models } = useModels();
  const { safeModeEnabled } = useSafeMode();

  if (!isConnected) {
    return (
      <div className="min-h-screen">
        <div className="container mx-auto py-16">
          <EmptyState
            icon={Database}
            title="Welcome to NL→SQL Agent"
            description="Connect to your database to start querying with natural language"
            action={{
              label: 'Go to Playground',
              onClick: () => navigate('/playground'),
            }}
          />
        </div>
      </div>
    );
  }

  const dbCount = schemas?.databases.length || 0;
  const schemaCount =
    schemas?.databases.reduce((acc, db) => acc + db.schemas.length, 0) || 0;
  const defaultModel = models.find((m) => m.name.includes('llama')) || models[0];

  return (
    <div className="min-h-screen">
      <div className="container mx-auto py-8 space-y-8">
        <div>
          <h1 className="text-4xl font-bold mb-2 text-slate-50">Dashboard</h1>
          <p className="text-slate-200">
            Overview of your connected database and capabilities
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Database className="w-4 h-4" />
                Databases
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{dbCount}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {schemaCount} schemas detected
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                AI Model
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg font-bold truncate" title={defaultModel?.name}>
                {defaultModel?.name || 'Loading...'}
              </div>
              <Badge variant="secondary" className="mt-2 text-xs">
                Default
              </Badge>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Shield className="w-4 h-4" />
                Safety Mode
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg font-bold">
                {safeModeEnabled ? 'Read-Only' : 'Full Access'}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {safeModeEnabled ? 'Only SELECT queries allowed' : 'All operations enabled'}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Activity className="w-4 h-4" />
                Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Badge variant="default" className="gap-1">
                <div className="w-2 h-2 rounded-full bg-current animate-pulse" />
                Connected
              </Badge>
              <p className="text-xs text-muted-foreground mt-2">
                {connection?.default_database}
              </p>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Try Example Queries</CardTitle>
            <CardDescription>
              Click any query to open it in the playground
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {EXAMPLE_QUERIES.map((query, idx) => (
                <Button
                  key={idx}
                  variant="outline"
                  className="justify-start h-auto py-3 px-4 text-left"
                  onClick={() => {
                    localStorage.setItem('last_nlq_query', query);
                    navigate('/playground');
                  }}
                >
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center text-sm font-semibold flex-shrink-0 mt-0.5">
                      {idx + 1}
                    </div>
                    <span className="text-sm">{query}</span>
                  </div>
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-center">
          <Button size="lg" onClick={() => navigate('/playground')} className="gap-2">
            <Sparkles className="w-4 h-4" />
            Open Playground
          </Button>
        </div>
      </div>
    </div>
  );
};
