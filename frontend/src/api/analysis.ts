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
}

export interface AnalysisResult {
  nodes: AnalysisNode[];
  edges: AnalysisEdge[];
}

export async function analyzeFiles(files: FileList): Promise<AnalysisResult> {
  const formData = new FormData();
  Array.from(files).forEach((file) => formData.append('files', file));
  const response = await client.post<AnalysisResult>('/api/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}
