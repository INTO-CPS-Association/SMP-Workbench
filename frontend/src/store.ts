import type { AnalysisResult } from './api/analysis';
import type { Node, Edge } from '@xyflow/react';

// Module-level store for passing data between routes without serialization constraints
let pendingFiles: FileList | null = null;
let analysisResult: AnalysisResult | null = null;
let currentGraph: { nodes: Node[]; edges: Edge[] } | null = null;

export const store = {
  getPendingFiles: () => pendingFiles,
  setPendingFiles: (files: FileList | null) => { pendingFiles = files; },

  getAnalysisResult: () => analysisResult,
  setAnalysisResult: (result: AnalysisResult | null) => { analysisResult = result; },

  getCurrentGraph: () => currentGraph,
  setCurrentGraph: (graph: { nodes: Node[]; edges: Edge[] } | null) => { currentGraph = graph; },
};
