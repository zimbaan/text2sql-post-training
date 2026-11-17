import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { useConnection } from '@/hooks/useConnection';
import { useSchemas } from '@/hooks/useSchemas';
import { NLQRunPayload } from '@/lib/types';
import { AlertCircle, Play, FileText, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useSafeMode } from '@/hooks/useSafeMode';
import { useSelectedModel } from '@/hooks/useSelectedModel';

interface NLQueryBoxProps {
  onExplain: (payload: NLQRunPayload) => void;
  onRun: (payload: NLQRunPayload) => void;
  selectedTables: string[];
  onSetTables?: (tables: string[]) => void;
  isRunning?: boolean;
  isExplaining?: boolean;
}

const EXAMPLE_QUERIES = [
  'Show me all users who signed up in the last 30 days',
  'What are the top 10 products by revenue?',
  'Count active subscriptions by plan type',
];

export const NLQueryBox = ({
  onExplain,
  onRun,
  selectedTables,
  onSetTables,
  isRunning,
  isExplaining,
}: NLQueryBoxProps) => {
  const { connectionId, connection, clearStaleConnection } = useConnection();
  const { schemas, error: schemasError, isLoading: schemasLoading } = useSchemas(connectionId, clearStaleConnection);
  const { safeModeEnabled, isLoading: safeModeLoading, setSafeMode } = useSafeMode();
  const { model } = useSelectedModel();
  const [query, setQuery] = useState('');
  const [selectedDatabase, setSelectedDatabase] = useState<string>('');
  const [selectedSchema, setSelectedSchema] = useState<string>('');
  const [returnSqlOnly, setReturnSqlOnly] = useState(false);
  const [allowModification, setAllowModification] = useState(false);

  // Load saved query from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('last_nlq_query');
    if (saved) setQuery(saved);
  }, []);

  // Save query to localStorage
  useEffect(() => {
    if (query) {
      localStorage.setItem('last_nlq_query', query);
    }
  }, [query]);

  // Set default database and schema
  useEffect(() => {
    if (schemas?.databases?.length && !selectedDatabase) {
      // For SQLite default_database is the file path, which isn't in the list ("main"): fall back to the first.
      const listed = schemas.databases.some((d) => d.name === connection?.default_database);
      const defaultDb = listed ? connection!.default_database : schemas.databases[0].name;
      setSelectedDatabase(defaultDb);
      const db = schemas.databases.find((d) => d.name === defaultDb);
      if (db?.schemas?.length) {
        setSelectedSchema(db.schemas[0].name);
      }
    }
  }, [schemas, connection, selectedDatabase]);

  // Auto-select all tables when a schema is selected
  useEffect(() => {
    if (!schemas || !selectedSchema || !selectedDatabase || !onSetTables) return;
    const db = schemas.databases.find((d) => d.name === selectedDatabase);
    const schema = db?.schemas?.find((s) => s.name === selectedSchema);
    if (schema?.tables) {
      const allTables = schema.tables.map((t) => `${selectedSchema}.${t.name}`);
      onSetTables(allTables);
    }
  }, [schemas, selectedSchema, selectedDatabase, onSetTables]);

  const handleExplain = () => {
    if (!query.trim() || !connectionId) return;
    const payload: NLQRunPayload = {
      user_query: query,
      database: selectedDatabase || undefined,
      schema: selectedSchema || undefined,
      table_scope: selectedTables.length > 0 ? selectedTables : undefined,
      return_sql_only: returnSqlOnly,
      allow_modification: allowModification,
      confirm_execution: false,
      model: model || undefined,
    };
    onExplain(payload);
  };

  const handleRun = () => {
    if (!query.trim() || !connectionId) return;
    let confirmExecution = false;
    if (allowModification && !safeModeEnabled && !returnSqlOnly) {
      const confirmed = window.confirm(
        'This will execute a CREATE/UPDATE/DELETE statement. Do you want to proceed?'
      );
      if (!confirmed) return;
      confirmExecution = true;
    }
    const payload: NLQRunPayload = {
      user_query: query,
      database: selectedDatabase || undefined,
      schema: selectedSchema || undefined,
      table_scope: selectedTables.length > 0 ? selectedTables : undefined,
      return_sql_only: returnSqlOnly,
      allow_modification: allowModification,
      confirm_execution: confirmExecution,
      model: model || undefined,
    };
    onRun(payload);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleRun();
    } else if (e.key === 'Enter' && e.shiftKey) {
      e.preventDefault();
      handleExplain();
    }
  };

  useEffect(() => {
    if (safeModeEnabled) {
      setAllowModification(false);
    }
  }, [safeModeEnabled]);

  const isReadOnly = safeModeEnabled;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Natural Language Query</CardTitle>
      </CardHeader>
        <CardContent className="space-y-4 text-slate-900">
        {!connectionId && (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Please connect to a database first
            </AlertDescription>
          </Alert>
        )}
        
        {connectionId && schemasError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Connection lost. Please reconnect to your database.
            </AlertDescription>
          </Alert>
        )}
        
        {connectionId && !schemasError && schemasLoading && (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Loading database schemas...
            </AlertDescription>
          </Alert>
        )}

        <div className="space-y-2">
          <Label htmlFor="query">Ask a question about your data</Label>
          <Textarea
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g., Show me all customers who made a purchase in the last month"
            className="min-h-[100px]"
            disabled={!connectionId}
          />
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_QUERIES.map((example) => (
              <Badge
                key={example}
                variant="secondary"
                className="cursor-pointer bg-slate-800 text-slate-100 hover:bg-slate-700 transition-colors"
                onClick={() => setQuery(example)}
              >
                {example}
              </Badge>
            ))}
          </div>
        </div>

        {connectionId && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="database">Database</Label>
              <Select 
                value={selectedDatabase} 
                onValueChange={setSelectedDatabase} 
                disabled={schemasLoading || !schemas?.databases?.length}
              >
                <SelectTrigger id="database">
                  <SelectValue placeholder={schemasLoading ? "Loading..." : "Select database"} />
                </SelectTrigger>
                <SelectContent>
                  {schemas?.databases?.map((db) => (
                    <SelectItem key={db.name} value={db.name}>
                      {db.name}
                    </SelectItem>
                  )) || []}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="schema">Schema</Label>
              <Select 
                value={selectedSchema} 
                onValueChange={setSelectedSchema} 
                disabled={schemasLoading || !(schemas?.databases?.length) || !selectedDatabase}
              >
                <SelectTrigger id="schema">
                  <SelectValue placeholder={schemasLoading ? "Loading..." : "Select schema"} />
                </SelectTrigger>
                <SelectContent>
                  {schemas?.databases
                    ?.find((db) => db.name === selectedDatabase)
                    ?.schemas?.map((schema) => (
                      <SelectItem key={schema.name} value={schema.name}>
                        {schema.name}
                      </SelectItem>
                    )) || []}
                </SelectContent>
              </Select>
            </div>
          </div>
        )}

        {selectedTables.length > 0 && (
          <div>
            <Label>Table Scope</Label>
            <div className="flex flex-wrap gap-2 mt-2">
              {selectedTables.map((table) => (
                <Badge key={table} variant="secondary">
                  {table}
                </Badge>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="safe-mode">Safe Mode (read-only)</Label>
              <p className="text-xs text-muted-foreground">
                Turn off to allow DML/DDL generation.
              </p>
            </div>
            <Switch
              id="safe-mode"
              checked={safeModeEnabled}
              onCheckedChange={(value) => setSafeMode(value)}
              disabled={safeModeLoading || !connectionId}
            />
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="return-sql">Return SQL Only</Label>
            <Switch
              id="return-sql"
              checked={returnSqlOnly}
              onCheckedChange={setReturnSqlOnly}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="allow-mod">Allow Modification</Label>
              <p className="text-xs text-muted-foreground">
                Enable INSERT, UPDATE, DELETE queries
              </p>
            </div>
            <Switch
              id="allow-mod"
              checked={allowModification}
              onCheckedChange={setAllowModification}
              disabled={isReadOnly || safeModeLoading}
            />
          </div>
        </div>

        <div className="flex gap-2">
          <Button
            onClick={handleExplain}
            variant="outline"
            disabled={!query.trim() || !connectionId || isExplaining}
            className="flex-1"
          >
            {isExplaining ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <FileText className="mr-2 h-4 w-4" />
            )}
            Explain (Shift+Enter)
          </Button>
          <Button
            onClick={handleRun}
            disabled={!query.trim() || !connectionId || isRunning}
            className="flex-1"
          >
            {isRunning ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            Run (Ctrl/Cmd+Enter)
          </Button>
        </div>

        <p className="text-xs text-muted-foreground">
          Tip: Use Ctrl/⌘+Enter to run or Shift+Enter to explain
        </p>
      </CardContent>
    </Card>
  );
};
