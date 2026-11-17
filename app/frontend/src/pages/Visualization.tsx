import { useEffect, useState } from 'react';
import { useConnection } from '@/hooks/useConnection';
import { useVisualize } from '@/hooks/useVisualize';
import { ConnectionForm } from '@/features/connection/ConnectionForm';
import { SchemaBrowser } from '@/features/schemas/SchemaBrowser';
import { TablePicker } from '@/features/schemas/TablePicker';
import { RelationshipGraph } from '@/features/visual/RelationshipGraph';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export const Visualization = () => {
  const { connectionId, clearStaleConnection } = useConnection();
  const { visualize, graph, isLoading, error } = useVisualize(connectionId);
  const { toast } = useToast();

  const [selectedTables, setSelectedTables] = useState<string[]>([]);
  const [schemaBrowserOpen, setSchemaBrowserOpen] = useState(true);

  // Reset selections and graph view if connection is cleared/lost
  useEffect(() => {
    if (!connectionId) {
      setSelectedTables([]);
    }
  }, [connectionId]);

  const handleTableSelect = (tableName: string, selected: boolean) => {
    setSelectedTables((prev) =>
      selected ? [...prev, tableName] : prev.filter((t) => t !== tableName)
    );
  };

  const handleRemoveTable = (tableName: string) => {
    setSelectedTables((prev) => prev.filter((t) => t !== tableName));
  };

  const handleVisualize = () => {
    if (!connectionId) {
      toast({
        title: 'No connection',
        description: 'Connect to a database first.',
        variant: 'destructive',
      });
      return;
    }

    if (selectedTables.length === 0) {
      toast({
        title: 'No tables selected',
        description: 'Choose at least one table to visualize.',
        variant: 'destructive',
      });
      return;
    }

    const schema = selectedTables[0].includes('.')
      ? selectedTables[0].split('.')[0]
      : undefined;

    visualize(
      {
        tables: selectedTables,
        schema: schema || undefined,
      },
      {
        onError: (e: any) => {
          toast({
            title: 'Visualization failed',
            description: e?.message || 'Could not build relationship graph.',
            variant: 'destructive',
          });
        },
      }
    );
  };

  return (
    <div className="min-h-screen">
      <div className="container mx-auto px-6 py-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-50">Schema Visualization</h1>
            <p className="text-sm text-slate-200">
              Explore table relationships in a dedicated canvas.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleVisualize} disabled={isLoading}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh Graph
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-4 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Connection</CardTitle>
              </CardHeader>
              <CardContent>
                <ConnectionForm />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex items-center justify-between">
                <CardTitle className="text-sm">Schema Browser</CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs"
                  onClick={() => setSchemaBrowserOpen((o) => !o)}
                >
                  {schemaBrowserOpen ? 'Hide' : 'Show'}
                </Button>
              </CardHeader>
              <CardContent className="space-y-3">
                {schemaBrowserOpen && connectionId ? (
                  <SchemaBrowser
                    connectionId={connectionId}
                    selectedTables={selectedTables}
                    onTableSelect={handleTableSelect}
                    onConnectionLost={clearStaleConnection}
                  />
                ) : (
                  <p className="text-sm text-muted-foreground">
                    {connectionId
                      ? 'Schema browser hidden'
                      : 'Connect to a database to browse tables.'}
                  </p>
                )}
              </CardContent>
            </Card>

            <TablePicker
              selectedTables={selectedTables}
              onRemove={handleRemoveTable}
              onVisualize={handleVisualize}
            />

            {error && (
              <Card className="border-destructive/40">
                <CardContent className="flex items-center gap-2 py-3 text-destructive text-sm">
                  <AlertTriangle className="w-4 h-4" />
                  {error.message}
                </CardContent>
              </Card>
            )}
          </div>

          <div className="col-span-8 space-y-3">
            <Card>
              <CardContent className="py-3 flex items-center gap-3 text-sm text-muted-foreground">
                <Badge variant="secondary">{selectedTables.length} tables selected</Badge>
                <Separator orientation="vertical" className="h-4" />
                <span>
                  Click <strong>Refresh Graph</strong> after selecting tables to see relationships.
                </span>
              </CardContent>
            </Card>

            {connectionId ? (
              <RelationshipGraph
                graph={graph}
                isLoading={isLoading}
                height={720}
                className="h-full"
              />
            ) : (
              <Card>
                <CardContent className="py-12 text-center text-muted-foreground">
                  Connect to a database to visualize relationships.
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
