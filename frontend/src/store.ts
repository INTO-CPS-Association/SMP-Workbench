import type { AnalysisResult } from './api/analysis';

// Module-level store for passing data between routes without serialization constraints
let pendingFiles: FileList | null = null;
let analysisResult: AnalysisResult | null = null;

export const store = {
  getPendingFiles: () => pendingFiles,
  setPendingFiles: (files: FileList | null) => { pendingFiles = files; },

  getAnalysisResult: () => analysisResult,
  setAnalysisResult: (result: AnalysisResult | null) => { analysisResult = result; },
};
