import axios from 'axios';

const api = axios.create({
    baseURL: window.smpWorkbench?.apiBaseUrl || import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
});

export default api;
