/**
 * VECTOR Configuration Module
 * Dynamically resolves API and WebSocket base URLs for local development,
 * custom environments, Vercel, and Render deployments.
 */

export const getApiBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim()) {
    const clean = envUrl.trim().replace(/\/+$/, '');
    return clean.endsWith('/api') ? clean : `${clean}/api`;
  }
  return 'http://127.0.0.1:8000/api';
};

export const getWebSocketUrl = (path: string): string => {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const envWs = import.meta.env.VITE_WS_URL;

  if (envWs && typeof envWs === 'string' && envWs.trim()) {
    return `${envWs.trim().replace(/\/+$/, '')}${cleanPath}`;
  }

  // Derive WebSocket URL from VITE_API_URL if provided
  const envApi = import.meta.env.VITE_API_URL;
  if (envApi && typeof envApi === 'string' && envApi.trim()) {
    try {
      const parsed = new URL(envApi);
      const wsProtocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${wsProtocol}//${parsed.host}${cleanPath}`;
    } catch {
      // Fallback to local default
    }
  }

  return `ws://127.0.0.1:8000${cleanPath}`;
};

export const config = {
  apiBase: getApiBaseUrl(),
  getWsUrl: getWebSocketUrl,
};

export default config;
