import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useHistory } from '@/hooks/useHistory';
import { ChevronDown, ChevronRight, Play, FileCode, Clock, AlertTriangle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { AccountHistoryItem } from '@/lib/types';
import { Skeleton } from '@/components/ui/skeleton';

interface HistoryPanelProps {
  onRerun: (query: string) => void;
  onLoadToPlayground: (query: string) => void;
}

export const HistoryPanel = ({ onRerun, onLoadToPlayground }: HistoryPanelProps) => {
  const { history, isLoading } = useHistory();
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  const toggleExpand = (id: string) => {
    setExpandedItems((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Group by day
  const groupedHistory = history.reduce((acc, item) => {
    const date = new Date(item.created_at);
    const dayKey = date.toDateString();
    if (!acc[dayKey]) acc[dayKey] = [];
    acc[dayKey].push(item);
    return acc;
  }, {} as Record<string, AccountHistoryItem[]>);

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-center text-muted-foreground">No query history yet</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <ScrollArea className="h-[600px]">
      <div className="space-y-4">
        {Object.entries(groupedHistory).map(([day, items]) => (
          <div key={day}>
            <h3 className="text-sm font-semibold mb-2 text-muted-foreground">{day}</h3>
            <div className="space-y-2">
              {items.map((item) => {
                const isExpanded = expandedItems.has(item.id);
                return (
                  <Card key={item.id}>
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-auto p-0 hover:bg-transparent"
                              onClick={() => toggleExpand(item.id)}
                            >
                              {isExpanded ? (
                                <ChevronDown className="w-4 h-4" />
                              ) : (
                                <ChevronRight className="w-4 h-4" />
                              )}
                            </Button>
                            <span className="text-xs text-muted-foreground">
                              {formatDistanceToNow(new Date(item.created_at), { addSuffix: true })}
                            </span>
                          </div>
                          <p className="text-sm font-medium line-clamp-2">{item.user_query}</p>
                        </div>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onLoadToPlayground(item.user_query)}
                            title="Load to playground"
                          >
                            <FileCode className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onRerun(item.user_query)}
                            title="Re-run query"
                          >
                            <Play className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                    {isExpanded && (
                      <CardContent className="pt-0 space-y-3">
                        <div>
                          <p className="text-xs font-semibold mb-1">SQL</p>
                          <pre className="bg-muted p-2 rounded text-xs overflow-x-auto">
                            <code>{item.sql}</code>
                          </pre>
                        </div>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          {item.row_count !== undefined && (
                            <span>{item.row_count} rows</span>
                          )}
                          {item.elapsed_ms !== undefined && item.elapsed_ms !== null && (
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {item.elapsed_ms}ms
                            </span>
                          )}
                          {item.error && (
                            <Badge variant="destructive" className="gap-1">
                              <AlertTriangle className="w-3 h-3" />
                              Error
                            </Badge>
                          )}
                          {!item.error && item.status === 'success' && (
                            <Badge variant="secondary">Success</Badge>
                          )}
                        </div>
                        {item.warnings && item.warnings.length > 0 && (
                          <div className="space-y-1">
                            {item.warnings.map((warning, idx) => (
                              <div
                                key={idx}
                                className="text-xs text-warning flex items-start gap-1"
                              >
                                <AlertTriangle className="w-3 h-3 mt-0.5" />
                                <span>{warning}</span>
                              </div>
                            ))}
                          </div>
                        )}
                        {item.error && (
                          <div className="text-xs text-destructive p-2 bg-destructive/10 rounded">
                            {item.error}
                          </div>
                        )}
                      </CardContent>
                    )}
                  </Card>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </ScrollArea>
  );
};
