import { useState } from 'react';
import { ChevronDown, ChevronRight, Table, Key, Link as LinkIcon } from 'lucide-react';
import { useSchemas } from '@/hooks/useSchemas';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import { ColumnInfo, TableInfo } from '@/lib/types';

interface SchemaBrowserProps {
  connectionId: string | null;
  selectedTables: string[];
  onTableSelect: (tableName: string, selected: boolean) => void;
  onConnectionLost?: () => void;
}

export const SchemaBrowser = ({ connectionId, selectedTables, onTableSelect, onConnectionLost }: SchemaBrowserProps) => {
  const { schemas, isLoading, error } = useSchemas(connectionId, onConnectionLost);
  const [expandedDatabases, setExpandedDatabases] = useState<Set<string>>(new Set());
  const [expandedSchemas, setExpandedSchemas] = useState<Set<string>>(new Set());
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());
  
  // Show error if connection is lost - AFTER all hooks are called
  if (error) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        Connection lost. Please reconnect to your database.
      </div>
    );
  }

  const toggleDatabase = (dbName: string) => {
    setExpandedDatabases((prev) => {
      const next = new Set(prev);
      if (next.has(dbName)) {
        next.delete(dbName);
      } else {
        next.add(dbName);
      }
      return next;
    });
  };

  const toggleSchema = (key: string) => {
    setExpandedSchemas((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const toggleTable = (key: string) => {
    setExpandedTables((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-2 p-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-8 w-full" />
        ))}
      </div>
    );
  }

  if (!schemas || !schemas.databases || schemas.databases.length === 0) {
    return null;
  }

  return (
    <ScrollArea className="h-80">
      <div className="p-3 space-y-2">
        {schemas.databases.map((database) => (
          <div key={database.name}>
            <div
              className="flex items-center gap-2 py-1 cursor-pointer hover:bg-muted/50 rounded px-2"
              onClick={() => toggleDatabase(database.name)}
            >
              {expandedDatabases.has(database.name) ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
              <span className="font-semibold">{database.name}</span>
            </div>

            {expandedDatabases.has(database.name) && database.schemas && (
              <div className="ml-3 space-y-1">
                {database.schemas.map((schema) => {
                  const schemaKey = `${database.name}.${schema.name}`;
                  return (
                    <div key={schemaKey}>
                      <div
                        className="flex items-center gap-2 py-1 cursor-pointer hover:bg-muted/50 rounded px-2"
                        onClick={() => toggleSchema(schemaKey)}
                      >
                        {expandedSchemas.has(schemaKey) ? (
                          <ChevronDown className="w-4 h-4" />
                        ) : (
                          <ChevronRight className="w-4 h-4" />
                        )}
                        <span className="text-sm font-medium">{schema.name}</span>
                      </div>

                      {expandedSchemas.has(schemaKey) && schema.tables && (
                        <div className="ml-3 space-y-1">
                          <div className="flex items-center justify-between px-2 py-1">
                            <div className="text-xs text-muted-foreground">Tables</div>
                            <div className="flex items-center gap-2 text-xs">
                              <Checkbox
                                checked={schema.tables.every((t) =>
                                  selectedTables.includes(`${schema.name}.${t.name}`)
                                )}
                                onCheckedChange={(checked) => {
                                  schema.tables.forEach((t) =>
                                    onTableSelect(`${schema.name}.${t.name}`, checked as boolean)
                                  );
                                }}
                              />
                              <span className="cursor-pointer select-none">Select all</span>
                            </div>
                          </div>
                          {schema.tables.map((table) => {
                            const tableKey = `${schemaKey}.${table.name}`;
                            const fullTableName = `${schema.name}.${table.name}`;
                            const isSelected = selectedTables.includes(fullTableName);

                            return (
                              <div key={tableKey}>
                                <div className="flex items-center gap-2 py-1 hover:bg-muted/50 rounded px-2">
                                  <Checkbox
                                    checked={isSelected}
                                    onCheckedChange={(checked) =>
                                      onTableSelect(fullTableName, checked as boolean)
                                    }
                                    onClick={(e) => e.stopPropagation()}
                                  />
                                  <div
                                    className="flex items-center gap-2 flex-1 cursor-pointer"
                                    onClick={() => toggleTable(tableKey)}
                                  >
                                    {expandedTables.has(tableKey) ? (
                                      <ChevronDown className="w-3 h-3" />
                                    ) : (
                                      <ChevronRight className="w-3 h-3" />
                                    )}
                                    <Table className="w-3 h-3" />
                                    <span className="text-sm">{table.name}</span>
                                    {table.approx_row_count !== undefined && (
                                      <Badge variant="secondary" className="text-xs">
                                        ~{table.approx_row_count}
                                      </Badge>
                                    )}
                                  </div>
                                </div>

                                {expandedTables.has(tableKey) && table.columns && (
                                  <div className="ml-8 space-y-0.5">
                                    {table.columns.map((column) => (
                                      <ColumnItem key={column.name} column={column} />
                                    ))}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </ScrollArea>
  );
};

const ColumnItem = ({ column }: { column: ColumnInfo }) => {
  return (
    <div className="flex items-center gap-2 py-0.5 text-xs text-muted-foreground px-2">
      <div className="flex items-center gap-1 min-w-0 flex-1">
        <span className="truncate">{column.name}</span>
        <span className="text-muted-foreground/60">({column.type})</span>
      </div>
      <div className="flex items-center gap-1">
        {column.is_primary_key && (
          <Badge variant="default" className="text-[10px] h-4 px-1">
            <Key className="w-2 h-2" />
          </Badge>
        )}
        {column.is_foreign_key && (
          <Badge variant="secondary" className="text-[10px] h-4 px-1">
            <LinkIcon className="w-2 h-2" />
          </Badge>
        )}
      </div>
    </div>
  );
};
