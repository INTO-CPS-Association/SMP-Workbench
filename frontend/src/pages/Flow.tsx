import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Background,
  Controls,
  useReactFlow,
  ConnectionMode,
  MarkerType,
} from '@xyflow/react';
import type { Connection, Node, Edge } from '@xyflow/react';
import { useLocation, useNavigate } from 'react-router-dom';

import '@xyflow/react/dist/style.css';
import '../index.css';

// @ts-ignore
import Sidebar from './Sidebar';
// @ts-ignore
import { DnDProvider, useDnD } from './DnDContext';
import { RoundDefaultNode } from './CustomNodes';
import { LabeledEdge } from './CustomEdge';
import { store } from '../store';
import type { AnalysisResult } from '../api/analysis';

const nodeTypes = { circleDefault: RoundDefaultNode };
const edgeTypes = { labeled: LabeledEdge };

const DEFAULT_EDGE_OPTIONS = {
  type: 'labeled',
  markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
  style: { strokeWidth: 1.5, stroke: 'var(--accent)', opacity: 0.85 },
  data: { probability: 0.0, avgSojournTime: 0.0 },
};

let id = 0;
const getId = () => `dndnode_${id++}`;

function circularLayout(count: number) {
  const radius = Math.max(300, count * 80);
  const cx = 500, cy = 300;
  return Array.from({ length: count }, (_, i) => {
    const angle = (2 * Math.PI * i) / count - Math.PI / 2;
    return { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) };
  });
}

function buildFromAnalysis(result: AnalysisResult): { nodes: Node[]; edges: Edge[] } {
  const positions = circularLayout(result.nodes.length);
  const nodes: Node[] = result.nodes.map((n, i) => ({
    id: n.id,
    type: 'circleDefault',
    position: positions[i],
    data: { label: n.label },
  }));
  const edges: Edge[] = result.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    ...DEFAULT_EDGE_OPTIONS,
    data: {
      probability: e.probability,
      avgSojournTime: e.avgSojournTime,
      transitionCount: e.transitionCount,
      cleanSojournTimes: e.cleanSojournTimes,
    },
  }));
  return { nodes, edges };
}

const DnDFlow = () => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const { screenToFlowPosition } = useReactFlow();
  const [type] = useDnD();
  const [ghostPos, setGhostPos] = useState<{ x: number; y: number } | null>(null);

  // Populate graph from analysis result, loaded project, or persisted session graph
  useEffect(() => {
    const analysisResult: AnalysisResult | null = store.getAnalysisResult();
    const locationGraph = (location.state as any)?.graph;
    const sessionGraph = store.getCurrentGraph();

    if (analysisResult) {
      const { nodes: n, edges: e } = buildFromAnalysis(analysisResult);
      setNodes(n);
      setEdges(e);
      store.setQuarantinedEntries(analysisResult.quarantined ?? []);
      store.setSuspiciousFiles(analysisResult.suspiciousFiles ?? []);
      store.setAnalysisResult(null);
      store.setCurrentGraph({ nodes: n, edges: e });
    } else if (locationGraph) {
      setNodes(locationGraph.nodes ?? []);
      setEdges(locationGraph.edges ?? []);
      store.setCurrentGraph({ nodes: locationGraph.nodes ?? [], edges: locationGraph.edges ?? [] });
    } else if (sessionGraph) {
      setNodes(sessionGraph.nodes);
      setEdges(sessionGraph.edges);
    }
  }, []);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  const onDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
    const rect = reactFlowWrapper.current?.getBoundingClientRect();
    if (rect) setGhostPos({ x: event.clientX - rect.left, y: event.clientY - rect.top });
  }, []);

  const onDragLeave = useCallback(() => setGhostPos(null), []);

  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setGhostPos(null);
      if (!type) return;
      const position = screenToFlowPosition({ x: event.clientX - 40, y: event.clientY - 40 });
      setNodes((nds) => nds.concat({ id: getId(), type, position, data: { label: 'Node' } }));
    },
    [screenToFlowPosition, type, setNodes],
  );

  const onSave = useCallback(() => {
    const blob = new Blob([JSON.stringify({ nodes, edges }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'graph.json';
    a.click();
    URL.revokeObjectURL(url);
  }, [nodes, edges]);

  const onSaveAs = useCallback(async () => {
    const json = JSON.stringify({ nodes, edges }, null, 2);
    if ('showSaveFilePicker' in window) {
      try {
        const fileHandle = await (window as any).showSaveFilePicker({
          suggestedName: 'graph.json',
          types: [{ description: 'JSON File', accept: { 'application/json': ['.json'] } }],
        });
        const writable = await fileHandle.createWritable();
        await writable.write(json);
        await writable.close();
      } catch { /* user cancelled */ }
    } else {
      const filename = window.prompt('Filename:', 'graph');
      if (!filename) return;
      const blob = new Blob([json], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename.endsWith('.json') ? filename : `${filename}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }
  }, [nodes, edges]);

  const onStatistics = useCallback(() => {
    store.setCurrentGraph({ nodes, edges });
    navigate('/statistics', { state: { nodes, edges } });
  }, [nodes, edges, navigate]);

  return (
    <div className="dndflow">
      <div
        className="reactflow-wrapper"
        ref={reactFlowWrapper}
        style={{ width: '100vw', height: '100vh', position: 'relative' }}
        onDragLeave={onDragLeave}
      >
        {ghostPos && (
          <div style={{
            position: 'absolute',
            left: ghostPos.x - 40, top: ghostPos.y - 40,
            width: 80, height: 80,
            borderRadius: '50%',
            border: '2px solid #0041d0',
            background: 'rgba(0, 65, 208, 0.06)',
            pointerEvents: 'none', opacity: 0.6, zIndex: 10,
          }} />
        )}
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onDrop={onDrop}
          onDragOver={onDragOver}
          connectionMode={ConnectionMode.Loose}
          defaultEdgeOptions={DEFAULT_EDGE_OPTIONS}
          fitView
        >
          <Controls />
          <Background />
        </ReactFlow>
      </div>
      <Sidebar onSave={onSave} onSaveAs={onSaveAs} onStatistics={onStatistics} />
    </div>
  );
};

export default function Flow() {
  return (
    <ReactFlowProvider>
      <DnDProvider>
        <DnDFlow />
      </DnDProvider>
    </ReactFlowProvider>
  );
}
