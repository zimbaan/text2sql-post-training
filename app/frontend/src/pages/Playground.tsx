import { useState } from 'react';
import { useConnection } from '@/hooks/useConnection';
import { useNLQ } from '@/hooks/useNLQ';
import { useVisualize } from '@/hooks/useVisualize';
import { ConnectionForm } from '@/features/connection/ConnectionForm';
import { SchemaBrowser } from '@/features/schemas/SchemaBrowser';
import { TablePicker } from '@/features/schemas/TablePicker';
import { NLQueryBox } from '@/features/nlq/NLQueryBox';
import { SQLPreview } from '@/features/nlq/SQLPreview';
import { ResultGrid } from '@/features/nlq/ResultGrid';
import { RelationshipGraph } from '@/features/visual/RelationshipGraph';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const formatErrorMessage = (error: any) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  if (detail?.error?.message) return detail.error.message;
  if (detail?.message) return detail.message;
  return error?.message || 'Request failed';
};

export const Playground = () => {
  const { connectionId, clearStaleConnection } = useConnection();
  const { run, explain, runResult, explainResult, isRunning, isExplaining, reset } = useNLQ(connectionId);
  const { visualize, graph, isLoading: isVisualizing } = useVisualize(connectionId);
  const { toast } = useToast();

  const [selectedTables, setSelectedTables] = useState<string[]>([]);
  const [isConnectionOpen, setIsConnectionOpen] = useState(!connectionId);
  const [isSchemaBrowserOpen, setIsSchemaBrowserOpen] = useState(true);

  const handleTableSelect = (tableName: string, selected: boolean) => {
    setSelectedTables((prev) =>
      selected ? [...prev, tableName] : prev.filter((t) => t !== tableName)
    );
  };

  const handleRemoveTable = (tableName: string) => {
    setSelectedTables((prev) => prev.filter((t) => t !== tableName));
  };

  const handleVisualize = () => {
    if (selectedTables.length === 0) {
      toast({
        title: 'No tables selected',
        description: 'Please select at least one table to visualize',
        variant: 'destructive',
      });
      return;
    }

    // Extract schema from first table (assuming all tables in same schema)
    const schema = selectedTables[0].split('.')[0];
    visualize({ tables: selectedTables, schema });
  };

  return (
    <div className="min-h-screen">
      <div className="grid grid-cols-12 gap-6 p-6">
        {/* Left Sidebar */}
        <div className="col-span-3 space-y-4">
          <Collapsible open={isConnectionOpen} onOpenChange={setIsConnectionOpen}>
            <CollapsibleTrigger asChild>
              <Button variant="outline" className="w-full justify-between">
                Connection
                {isConnectionOpen ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="mt-2">
                <ConnectionForm />
              </div>
            </CollapsibleContent>
          </Collapsible>

          {connectionId && (
            <>
              <Collapsible open={isSchemaBrowserOpen} onOpenChange={setIsSchemaBrowserOpen}>
                <CollapsibleTrigger asChild>
                  <Button variant="outline" className="w-full justify-between">
                    Schema Browser
                    {isSchemaBrowserOpen ? (
                      <ChevronUp className="w-4 h-4" />
                    ) : (
                      <ChevronDown className="w-4 h-4" />
                    )}
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="mt-2">
                    <SchemaBrowser
                      connectionId={connectionId}
                      selectedTables={selectedTables}
                      onTableSelect={handleTableSelect}
                      onConnectionLost={clearStaleConnection}
                    />
                  </div>
                </CollapsibleContent>
              </Collapsible>

              <TablePicker
                selectedTables={selectedTables}
                onRemove={handleRemoveTable}
                onVisualize={handleVisualize}
              />
            </>
          )}
        </div>

        {/* Main Content */}
        <div className="col-span-6 space-y-6">
          <NLQueryBox
            onExplain={(payload) => {
              reset();
              explain(payload, {
                onError: (error: any) => {
                  toast({
                    title: 'Explain failed',
                    description: formatErrorMessage(error),
                    variant: 'destructive',
                  });
                },
              });
            }}
            onRun={(payload) => {
              reset();
              run(payload, {
                onError: (error: any) => {
                  toast({
                    title: 'Query failed',
                    description: formatErrorMessage(error),
                    variant: 'destructive',
                  });
                },
              });
            }}
            selectedTables={selectedTables}
            onSetTables={setSelectedTables}
            isRunning={isRunning}
            isExplaining={isExplaining}
          />

          {(explainResult || runResult) && (
            <SQLPreview
              sql={explainResult?.sql || runResult?.sql || ''}
              explainResult={explainResult}
            />
          )}

          {runResult && (
            <ResultGrid result={runResult} sql={runResult.sql} connectionId={connectionId} />
          )}
        </div>

        {/* Right Sidebar - Graph */}
        <div className="col-span-3">
          <RelationshipGraph graph={graph} isLoading={isVisualizing} />
        </div>
      </div>
    </div>
  );
};
