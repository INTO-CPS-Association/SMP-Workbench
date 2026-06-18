import client from './client';
import { apiUrl } from './baseUrl';

export interface AnalysisNode {
  id: string;
  label: string;
}

export interface DistributionFit {
  distribution: string;
  pValue: number;
  ksStat: number;
}

export interface AnalysisEdge {
  id: string;
  source: string;
  target: string;
  probability: number;
  avgSojournTime: number;
  transitionCount: number;
  cleanSojournTimes: number[];
  distributionFit?: DistributionFit | null;
}

export interface QuarantinedEntry {
  fromState: string;
  toState: string;
  sojournTime: number;
  outlierScore: number;
}

export interface SuspiciousTransition {
  fromState: string;
  toState: string;
  sojournTime: number;
  outlierScore: number;
  isOutlier: boolean;
}

export interface SuspiciousFile {
  filename: string;
  transition: string;
  fromState: string;
  toState: string;
  count: number;
  avgCount: number;
  allCounts: number[];
  allFilenames: string[];
  transitions: SuspiciousTransition[];
}

export interface NormalFile {
  filename: string;
  /** edgeId (e.g. "state1-state2") → clean sojourn times for this file on that edge */
  edgeTimes: Record<string, number[]>;
}

export interface AnalysisResult {
  nodes: AnalysisNode[];
  edges: AnalysisEdge[];
  quarantined: QuarantinedEntry[];
  suspiciousFiles: SuspiciousFile[];
  normalFiles: NormalFile[];
}

export async function analyzeSojournOutliers(
  transitions: SuspiciousTransition[],
): Promise<SuspiciousTransition[]> {
  const response = await client.post<SuspiciousTransition[]>(
    '/api/analyze/sojourn-outliers',
    { transitions, method: 'iqr' },
  );
  return response.data;
}

export async function analyzeFilesStreaming(
  files: FileList,
  onProgress: (percent: number, message: string) => void,
): Promise<AnalysisResult> {
  const formData = new FormData();
  Array.from(files).forEach((file) => formData.append('files', file));

  const response = await fetch(apiUrl('/api/analyze/stream?method=iqr&file_method=iqr'), {
    method: 'POST',
    body: formData,
  });

  if (!response.ok || !response.body) {
    throw new Error(`Server error: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const payload = JSON.parse(line.slice(6)) as {
        percent?: number;
        message?: string;
        error?: string;
        result?: AnalysisResult;
      };
      if (payload.error) throw new Error(payload.error);
      if (typeof payload.percent === 'number') onProgress(payload.percent, payload.message ?? '');
      if (payload.result) return payload.result;
    }
  }
  throw new Error('Stream ended without a result.');
}
