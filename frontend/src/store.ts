import type { AnalysisResult, QuarantinedEntry, SuspiciousFile, NormalFile } from './api/analysis';
import type { Node, Edge } from '@xyflow/react';

export type OutlierMethod = 'lof' | 'iqr';

// Module-level store for passing data between routes without serialization constraints
let pendingFiles: FileList | null = null;
let analysisResult: AnalysisResult | null = null;
let currentGraph: { nodes: Node[]; edges: Edge[] } | null = null;
let quarantinedEntries: QuarantinedEntry[] = [];
let suspiciousFiles: SuspiciousFile[] = [];
let normalFiles: NormalFile[] = [];
let outlierMethod: OutlierMethod = 'lof';
let fileDetectionMethod: OutlierMethod = 'iqr';

export const store = {
  getPendingFiles: () => pendingFiles,
  setPendingFiles: (files: FileList | null) => { pendingFiles = files; },

  getOutlierMethod: () => outlierMethod,
  setOutlierMethod: (m: OutlierMethod) => { outlierMethod = m; },

  getFileDetectionMethod: () => fileDetectionMethod,
  setFileDetectionMethod: (m: OutlierMethod) => { fileDetectionMethod = m; },

  getAnalysisResult: () => analysisResult,
  setAnalysisResult: (result: AnalysisResult | null) => { analysisResult = result; },

  getCurrentGraph: () => currentGraph,
  setCurrentGraph: (graph: { nodes: Node[]; edges: Edge[] } | null) => { currentGraph = graph; },

  getQuarantinedEntries: () => quarantinedEntries,
  setQuarantinedEntries: (entries: QuarantinedEntry[]) => { quarantinedEntries = entries; },

  getSuspiciousFiles: () => suspiciousFiles,
  setSuspiciousFiles: (files: SuspiciousFile[]) => { suspiciousFiles = files; },

  getNormalFiles: () => normalFiles,
  setNormalFiles: (files: NormalFile[]) => { normalFiles = files; },

  reset: () => {
    pendingFiles = null;
    analysisResult = null;
    currentGraph = null;
    quarantinedEntries = [];
    suspiciousFiles = [];
    normalFiles = [];
  },
};
