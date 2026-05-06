import client from './client';

export interface AnalysisNode {
  id: string;
  label: string;
}

export interface AnalysisEdge {
  id: string;
  source: string;
  target: string;
  probability: number;
  avgSojournTime: number;
  transitionCount: number;
  cleanSojournTimes: number[];
}

export interface QuarantinedEntry {
  fromState: string;
  toState: string;
  sojournTime: number;
  outlierScore: number;
}

export interface SuspiciousFile {
  filename: string;
  transition: string;
  fromState: string;
  toState: string;
  count: number;
  avgCount: number;
  outlierScore: number;
}

export interface AnalysisResult {
  nodes: AnalysisNode[];
  edges: AnalysisEdge[];
  quarantined: QuarantinedEntry[];
  suspiciousFiles: SuspiciousFile[];
}

export async function analyzeFiles(files: FileList): Promise<AnalysisResult> {
  const formData = new FormData();
  Array.from(files).forEach((file) => formData.append('files', file));
  const response = await client.post<AnalysisResult>('/api/analyze', formData);
  return response.data;
}

export async function analyzeFilesStreaming(
  files: FileList,
  onProgress: (percent: number, message: string) => void,
): Promise<AnalysisResult> {
  const formData = new FormData();
  Array.from(files).forEach((file) => formData.append('files', file));

  const response = await fetch('http://localhost:8000/api/analyze/stream', {
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
