const { contextBridge } = require('electron');

const apiBaseUrlArg = process.argv.find((arg) => arg.startsWith('--smp-workbench-api-base-url='));
const apiBaseUrl = apiBaseUrlArg
  ? apiBaseUrlArg.slice('--smp-workbench-api-base-url='.length)
  : process.env.SMP_WORKBENCH_API_BASE_URL || '';

contextBridge.exposeInMainWorld('smpWorkbench', Object.freeze({
  apiBaseUrl,
}));
