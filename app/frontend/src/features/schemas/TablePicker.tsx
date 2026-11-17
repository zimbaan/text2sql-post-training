import { X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface TablePickerProps {
  selectedTables: string[];
  onRemove: (tableName: string) => void;
  onVisualize: () => void;
}

export const TablePicker = ({ selectedTables, onRemove, onVisualize }: TablePickerProps) => {
  return (
    <Card className="max-h-64 overflow-y-auto">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Selected Tables</CardTitle>
        <CardDescription className="text-xs">
          Tables to include in queries and visualization
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {selectedTables.length === 0 ? (
          <p className="text-sm text-muted-foreground">No tables selected</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {selectedTables.map((table) => (
              <Badge key={table} variant="secondary" className="gap-1 pr-1">
                {table}
                <button
                  onClick={() => onRemove(table)}
                  className="ml-1 rounded-full hover:bg-muted"
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}
          </div>
        )}
        {selectedTables.length > 0 && (
          <Button onClick={onVisualize} size="sm" className="w-full">
            Visualize Relationships
          </Button>
        )}
      </CardContent>
    </Card>
  );
};
