export {};

declare global {
  interface Window {
    smpWorkbench?: {
      apiBaseUrl: string;
    };
  }
}
