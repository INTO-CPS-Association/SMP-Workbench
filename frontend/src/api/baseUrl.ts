const fallbackApiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

export function getApiBaseUrl(): string {
  return window.smpWorkbench?.apiBaseUrl || fallbackApiBaseUrl;
}

export function apiUrl(path: string): string {
  return new URL(path, getApiBaseUrl()).toString();
}
