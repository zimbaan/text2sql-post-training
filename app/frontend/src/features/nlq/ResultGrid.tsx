import { useMemo, useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  SortingState,
  ColumnDef,
} from '@tanstack/react-table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  Pie,
  PieChart,
  XAxis,
  YAxis,
  Cell,
} from 'recharts';
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  ChartConfig,
} from '@/components/ui/chart';
import { Download, ArrowUpDown, Clock, AlertTriangle } from 'lucide-react';
import { NLQRunResult } from '@/lib/types';
import { useCsvExport } from '@/hooks/useCsvExport';
import { useToast } from '@/hooks/use-toast';

interface ResultGridProps {
  result: NLQRunResult | null;
  sql: string;
  connectionId: string | null;
}

type VizMode = 'auto' | 'table' | 'bar' | 'line' | 'pie';

export const ResultGrid = ({ result, sql, connectionId }: ResultGridProps) => {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [vizMode, setVizMode] = useState<VizMode>('auto');
  const [filename, setFilename] = useState(() => {
    const date = new Date();
    return `result_${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(
      date.getDate()
    ).padStart(2, '0')}_${String(date.getHours()).padStart(2, '0')}${String(
      date.getMinutes()
    ).padStart(2, '0')}.csv`;
  });
  const { exportCsv, isExporting } = useCsvExport(connectionId);
  const { toast } = useToast();

  const columns = useMemo<ColumnDef<any>[]>(() => {
    if (!result?.columns) return [];
    return result.columns.map((col) => ({
      accessorKey: col,
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
            className="hover:bg-muted"
          >
            {col}
            <ArrowUpDown className="ml-2 h-3 w-3" />
          </Button>
        );
      },
      cell: ({ getValue }) => {
        const value = getValue();
        return (
          <div
            className="max-w-[300px] truncate cursor-pointer hover:text-primary"
            onClick={() => {
              navigator.clipboard.writeText(String(value));
              toast({ description: 'Copied to clipboard' });
            }}
            title="Click to copy"
          >
            {value === null ? (
              <span className="text-muted-foreground italic">NULL</span>
            ) : (
              String(value)
            )}
          </div>
        );
      },
    }));
  }, [result, toast]);

  const data = useMemo(() => {
    if (!result?.rows || !result?.columns) return [];
    return result.rows.map((row) => {
      const obj: any = {};
      result.columns.forEach((col, idx) => {
        obj[col] = row[idx];
      });
      return obj;
    });
  }, [result]);

  const augmentedData = useMemo(
    () => data.map((row, idx) => ({ __index: idx + 1, ...row })),
    [data]
  );

  const columnTypes = useMemo(() => {
    if (!result?.columns) return [];

    const isNumericValue = (value: any) => {
      if (value === null || value === undefined) return false;
      if (typeof value === 'number') return Number.isFinite(value);
      if (typeof value === 'boolean') return false;
      const num = Number(value);
      return Number.isFinite(num);
    };

    return result.columns.map((col, colIdx) => {
      const sampleRow = result.rows?.find(
        (row) => row[colIdx] !== null && row[colIdx] !== undefined
      );
      const type = sampleRow && isNumericValue(sampleRow[colIdx]) ? 'numeric' : 'categorical';
      return { name: col, type };
    });
  }, [result]);

  const numericColumns = useMemo(
    () => columnTypes.filter((c) => c.type === 'numeric').map((c) => c.name),
    [columnTypes]
  );
  const categoricalColumns = useMemo(
    () => columnTypes.filter((c) => c.type === 'categorical').map((c) => c.name),
    [columnTypes]
  );

  const chartColors = ['#6366f1', '#22c55e', '#f59e0b', '#06b6d4', '#ef4444'];

  const chartConfig = useMemo<ChartConfig>(() => {
    return numericColumns.reduce((acc, col, idx) => {
      acc[col] = {
        label: col,
        color: chartColors[idx % chartColors.length],
      };
      return acc;
    }, {} as ChartConfig);
  }, [numericColumns]);

  const pickRecommendedViz = (): VizMode => {
    if (!result || result.row_count === 0 || augmentedData.length === 0) return 'table';
    if (numericColumns.length === 0) return 'table';
    if (numericColumns.length === 1 && categoricalColumns.length === 0) return 'line';
    if (numericColumns.length >= 1 && categoricalColumns.length >= 1) {
      return result.row_count > 8 ? 'line' : 'bar';
    }
    return 'line';
  };

  const recommendedViz = pickRecommendedViz();
  const resolvedViz = vizMode === 'auto' ? recommendedViz : vizMode;

  const xAxisKey = categoricalColumns[0] || result?.columns?.[0] || '__index';
  const pieValueKey = numericColumns[0];
  const pieLabelKey = categoricalColumns[0] || xAxisKey;

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    state: {
      sorting,
    },
  });

  const handleExport = () => {
    exportCsv(
      { sql, filename },
      {
        onSuccess: () => {
          toast({
            title: 'Export successful',
            description: `Downloaded ${filename}`,
          });
        },
        onError: (error: any) => {
          toast({
            title: 'Export failed',
            description: error.message,
            variant: 'destructive',
          });
        },
      }
    );
  };

  if (!result) return null;

  const rowCount = result.row_count ?? 0;
  const elapsedMs = result.elapsed_ms ?? 0;
  const columnsCount = result.columns?.length ?? 0;

  const renderChartContent = () => {
    if (resolvedViz === 'table') {
      return (
        <div className="rounded-md border overflow-auto max-h-[500px]">
          <Table>
            <TableHeader className="sticky top-0 bg-background z-10">
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <TableHead key={header.id}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(header.column.columnDef.header, header.getContext())}
                    </TableHead>
                  ))}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows?.length ? (
                table.getRowModel().rows.map((row) => (
                  <TableRow key={row.id}>
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={columns.length} className="h-24 text-center">
                    No results.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      );
    }

    if (augmentedData.length === 0 || numericColumns.length === 0) {
      return (
        <div className="border border-dashed rounded-lg p-6 text-sm text-muted-foreground text-center">
          No numeric fields available to visualize. Switch to the table view or run a query that returns numeric data.
        </div>
      );
    }

    if (resolvedViz === 'bar') {
      return (
        <ChartContainer config={chartConfig} className="border rounded-lg bg-card">
          <BarChart data={augmentedData} margin={{ left: 12, right: 12, top: 12, bottom: 12 }}>
            <CartesianGrid strokeDasharray="4 4" className="text-muted-foreground/40" />
            <XAxis dataKey={xAxisKey} tickLine={false} axisLine={false} tickMargin={8} />
            <YAxis tickLine={false} axisLine={false} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
            {numericColumns.map((key) => (
              <Bar key={key} dataKey={key} fill={`var(--color-${key})`} radius={4} />
            ))}
          </BarChart>
        </ChartContainer>
      );
    }

    if (resolvedViz === 'line') {
      return (
        <ChartContainer config={chartConfig} className="border rounded-lg bg-card">
          <LineChart data={augmentedData} margin={{ left: 12, right: 12, top: 12, bottom: 12 }}>
            <CartesianGrid strokeDasharray="4 4" className="text-muted-foreground/40" />
            <XAxis dataKey={xAxisKey} tickLine={false} axisLine={false} tickMargin={8} />
            <YAxis tickLine={false} axisLine={false} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
            {numericColumns.map((key) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={`var(--color-${key})`}
                strokeWidth={2}
                dot={{ strokeWidth: 1 }}
                activeDot={{ r: 4 }}
              />
            ))}
          </LineChart>
        </ChartContainer>
      );
    }

    if (resolvedViz === 'pie' && pieValueKey) {
      return (
        <ChartContainer
          config={{
            [pieValueKey]: { label: pieValueKey, color: chartColors[0] },
          }}
          className="border rounded-lg bg-card"
        >
          <PieChart>
            <Pie
              data={augmentedData}
              dataKey={pieValueKey}
              nameKey={pieLabelKey}
              innerRadius={60}
              outerRadius={120}
              paddingAngle={3}
            >
              {augmentedData.map((_, idx) => (
                <Cell key={`slice-${idx}`} fill={chartColors[idx % chartColors.length]} />
              ))}
            </Pie>
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
          </PieChart>
        </ChartContainer>
      );
    }

    return (
      <div className="border border-dashed rounded-lg p-6 text-sm text-muted-foreground text-center">
        Not enough data to build this chart. Try switching to Table view.
      </div>
    );
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="text-sm">Query Results</CardTitle>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span>{rowCount.toLocaleString()} rows</span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {elapsedMs}ms
              </span>
              {result.truncated && (
                <Badge variant="secondary" className="gap-1 bg-warning/20 text-warning border-warning">
                  <AlertTriangle className="w-3 h-3" />
                  Truncated
                </Badge>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Input
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              className="w-[200px]"
              placeholder="filename.csv"
            />
            <Button onClick={handleExport} disabled={isExporting} size="sm" className="gap-2">
              <Download className="w-4 h-4" />
              {isExporting ? 'Exporting...' : 'Export CSV'}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {result.warnings.length > 0 && (
          <div className="mb-4 space-y-2">
            {result.warnings.map((warning, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2 p-3 bg-warning/10 border border-warning rounded-lg"
              >
                <AlertTriangle className="w-4 h-4 text-warning mt-0.5" />
                <p className="text-sm">{warning}</p>
              </div>
            ))}
          </div>
        )}

        <div className="rounded-lg border bg-muted/40 p-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="text-sm font-medium">Data Visualization</div>
              <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                <Badge variant="secondary">
                  {rowCount.toLocaleString()} rows × {columnsCount} columns
                </Badge>
                <Badge variant="outline">
                  {numericColumns.length} numeric
                  {categoricalColumns.length ? `, ${categoricalColumns.length} categorical` : ''}
                </Badge>
              </div>
            </div>
            <div className="text-xs text-muted-foreground">
              Recommended: <span className="text-primary font-medium capitalize">{recommendedViz}</span>
            </div>
          </div>

          <Tabs value={vizMode} onValueChange={(value) => setVizMode(value as VizMode)}>
            <TabsList className="grid grid-cols-5 gap-1">
              <TabsTrigger value="auto">Auto</TabsTrigger>
              <TabsTrigger value="table">Table</TabsTrigger>
              <TabsTrigger value="bar">Bar Chart</TabsTrigger>
              <TabsTrigger value="line">Line Chart</TabsTrigger>
              <TabsTrigger value="pie" disabled={!pieValueKey}>
                Pie Chart
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <div>{renderChartContent()}</div>
        </div>
      </CardContent>
    </Card>
  );
};
