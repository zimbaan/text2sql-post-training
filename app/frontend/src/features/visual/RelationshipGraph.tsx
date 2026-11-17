import { memo, useEffect, useMemo, useState } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MiniMap,
  BackgroundVariant,
  getSmoothStepPath,
  EdgeProps,
  Handle,
  Position,
  BaseEdge,
  EdgeLabelRenderer,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { VisualGraph } from '@/lib/types';
import { Loader2 } from 'lucide-react';

interface RelationshipGraphProps {
  graph: VisualGraph | null | undefined;
  isLoading?: boolean;
  height?: number | string;
  className?: string;
}

const COLORS = [
  '#6366f1',
  '#22c55e',
  '#f59e0b',
  '#0ea5e9',
  '#ec4899',
  '#a855f7',
  '#14b8a6',
  '#e11d48',
];

export const RelationshipGraph = ({ graph, isLoading, height = 600, className }: RelationshipGraphProps) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null);

  const CardinalityEdge = ({
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    selected,
    style = {},
    data,
    markerEnd,
  }: EdgeProps) => {
    const [edgePath] = getSmoothStepPath({
      sourceX,
      sourceY,
      sourcePosition,
      targetX,
      targetY,
      targetPosition,
    });

    const sourceBadge = {
      x: sourceX + (sourcePosition === Position.Right ? 10 : -10),
      y:
        sourceY +
        (sourcePosition === Position.Bottom ? 12 : sourcePosition === Position.Top ? -12 : 0),
    };
    const targetBadge = {
      x: targetX + (targetPosition === Position.Right ? 10 : -10),
      y:
        targetY +
        (targetPosition === Position.Bottom ? 12 : targetPosition === Position.Top ? -12 : 0),
    };

    const baseStroke = selected ? '#ec4899' : '#6366f1';

    return (
      <>
        <BaseEdge
          id={id}
          path={edgePath}
          style={{
            ...style,
            stroke: baseStroke,
            strokeWidth: selected ? 3 : 2.4,
            strokeDasharray: selected ? '6 4' : '0',
            filter: selected ? 'drop-shadow(0px 0px 4px rgba(99,102,241,0.35))' : 'none',
          }}
          markerEnd={markerEnd}
        />
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(${sourceBadge.x}px, ${sourceBadge.y}px)`,
              pointerEvents: 'none',
            }}
          >
            <div className="w-6 h-6 rounded-md border border-primary bg-background text-xs font-semibold grid place-items-center shadow-sm">
              {String(data?.sourceCard ?? '')}
            </div>
          </div>
          <div
            style={{
              position: 'absolute',
              transform: `translate(${targetBadge.x}px, ${targetBadge.y}px)`,
              pointerEvents: 'none',
            }}
          >
            <div className="w-6 h-6 rounded-md border border-primary bg-background text-xs font-semibold grid place-items-center shadow-sm">
              {String(data?.targetCard ?? '')}
            </div>
          </div>
        </EdgeLabelRenderer>
      </>
    );
  };

  const TableNode = memo(({ data }: any) => {
    return (
      <div className="rounded-xl border bg-card shadow-lg min-w-[220px] overflow-hidden">
        <div
          className="px-3 py-2 text-sm font-semibold text-card-foreground"
          style={{ borderBottom: `1px solid ${data.color}` }}
        >
          {data.label}
        </div>
        <div className="max-h-[240px] overflow-auto">
          {(data.columns || []).map((col: any) => (
            <div
              key={col.name}
              className="flex items-center justify-between px-3 py-1 text-xs border-b last:border-none"
              style={{
                backgroundColor:
                  data.highlightColumns && data.highlightColumns.has(col.name)
                    ? 'rgba(99,102,241,0.12)'
                    : 'transparent',
                fontWeight:
                  data.highlightColumns && data.highlightColumns.has(col.name) ? 700 : 500,
              }}
            >
              <div className="flex items-center gap-2">
                {col.is_primary_key && <span className="text-amber-500 font-semibold">PK</span>}
                {col.is_foreign_key && <span className="text-sky-500 font-semibold">FK</span>}
                <span className="font-medium">{col.name}</span>
              </div>
              <span className="text-[11px] text-muted-foreground">{col.type}</span>
            </div>
          ))}
        </div>
        <Handle
          type="source"
          position={Position.Right}
          className="!w-3 !h-3 !bg-primary !border-primary/80"
          style={{ top: '50%', transform: 'translateY(-50%)', right: -6 }}
        />
        <Handle
          type="target"
          position={Position.Left}
          className="!w-3 !h-3 !bg-primary/70 !border-primary/60"
          style={{ top: '50%', transform: 'translateY(-50%)', left: -6 }}
        />
      </div>
    );
  });
  TableNode.displayName = 'TableNode';

  const nodeTypes = useMemo(
    () => ({
      table: TableNode,
    }),
    []
  );

  useEffect(() => {
    if (!graph) {
      setNodes([]);
      setEdges([]);
      return;
    }

    // Convert graph data to ReactFlow format
    // Prepare highlighted columns from selected edge
    const highlightSource = selectedEdge
      ? graph.edges.find((e, idx) => `edge-${idx}` === selectedEdge)?.source_column
      : null;
    const highlightTarget = selectedEdge
      ? graph.edges.find((e, idx) => `edge-${idx}` === selectedEdge)?.target_column
      : null;
    const highlightSourceTable = selectedEdge
      ? graph.edges.find((e, idx) => `edge-${idx}` === selectedEdge)?.source
      : null;
    const highlightTargetTable = selectedEdge
      ? graph.edges.find((e, idx) => `edge-${idx}` === selectedEdge)?.target
      : null;

    const reactFlowNodes: Node[] = graph.nodes.map((node, index) => {
      const color = COLORS[index % COLORS.length];
      const highlightColumns = new Set<string>();
      if (highlightSourceTable === node.id && highlightSource) highlightColumns.add(highlightSource);
      if (highlightTargetTable === node.id && highlightTarget) highlightColumns.add(highlightTarget);
      return {
        id: node.id,
        type: 'table',
        position: {
          x: (index % 3) * 360,
          y: Math.floor(index / 3) * 260,
        },
        data: { label: node.label, columns: node.columns || [], color, highlightColumns },
      };
    });

    const reactFlowEdges: Edge[] = graph.edges.map((edge, index) => {
      const card = edge.cardinality || '';
      const [sourceCard, targetCard] = card.includes(':') ? card.split(':') : ['', ''];
      return {
        id: `edge-${index}`,
        source: edge.source,
        target: edge.target,
        type: 'cardinality',
        animated: true,
        selectable: true,
        data: {
          sourceCard: sourceCard || 'N',
          targetCard: targetCard || '1',
        },
        style: { stroke: 'var(--muted-foreground)', strokeWidth: 2 },
        markerEnd: {
          type: 'arrowclosed',
        },
      };
    });

    setNodes(reactFlowNodes);
    setEdges(reactFlowEdges);
  }, [graph, setNodes, setEdges, selectedEdge]);

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-sm">Relationship Graph</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div style={{ height }} className="relative rounded-b-lg">
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-background/50">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : nodes.length === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center text-muted-foreground text-sm">
              Select tables and click "Visualize Relationships"
            </div>
          ) : (
            <div className="h-full w-full">
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onEdgeClick={(_, edge) => setSelectedEdge(edge.id)}
                nodeTypes={nodeTypes}
                edgeTypes={{ cardinality: CardinalityEdge }}
                fitView
                attributionPosition="bottom-left"
              >
                <Background variant={BackgroundVariant.Dots} gap={18} size={1} />
                <Controls />
                <MiniMap
                  nodeColor={(node) => COLORS[nodes.findIndex((n) => n.id === node.id) % COLORS.length]}
                  maskColor="hsl(var(--muted) / 0.8)"
                />
              </ReactFlow>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
