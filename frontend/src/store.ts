import type { AnalysisResult, QuarantinedEntry, SuspiciousFile, NormalFile, SuspiciousTransition } from './api/analysis';
import type { Node, Edge } from '@xyflow/react';

// Module-level store for passing data between routes without serialization constraints
let pendingFiles: FileList | null = null;
let analysisResult: AnalysisResult | null = null;
let currentGraph: { nodes: Node[]; edges: Edge[] } | null = null;
let quarantinedEntries: QuarantinedEntry[] = [];
let suspiciousFiles: SuspiciousFile[] = [];
let normalFiles: NormalFile[] = [];

interface StatsUIState {
  included: Set<number>;
  includedFilePairs: Set<string>;
  fileOutlierData: Map<string, SuspiciousTransition[]>;
  includedFileEntries: Set<string>;
  excludedClean: Map<string, Set<number>>;
  manuallyExcludedNormalFiles: Set<string>;
}
let statsUIState: StatsUIState | null = null;

export const store = {
  getPendingFiles: () => pendingFiles,
  setPendingFiles: (files: FileList | null) => { pendingFiles = files; },

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

  getStatsUIState: () => statsUIState,
  setStatsUIState: (state: StatsUIState) => { statsUIState = state; },

  reset: () => {
    pendingFiles = null;
    analysisResult = null;
    currentGraph = null;
    quarantinedEntries = [];
    suspiciousFiles = [];
    normalFiles = [];
    statsUIState = null;
  },
};
