import i18n from '@/shared/i18n';
import { ApiError } from './errors';
import type { ApiEnvelope, RequestOptions } from './contracts';
import { clearStoredToken, getStoredToken } from '@/shared/auth/storage';
import { DEV_MODE } from '@/shared/auth/AuthProvider';

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

export function buildApiUrl(path: string, query?: RequestOptions['query']) {
  const url = new URL(`${apiBaseUrl}${path}`, window.location.origin);

  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null || value === '') {
        continue;
      }

      url.searchParams.set(key, String(value));
    }
  }

  return apiBaseUrl ? url.toString() : `${url.pathname}${url.search}`;
}

async function parseError(response: Response) {
  const contentType = response.headers.get('content-type') ?? '';

  if (contentType.includes('application/json')) {
    const text = await response.text();
    if (text.trim()) {
      const payload = JSON.parse(text) as Partial<ApiEnvelope<unknown>>;
      return new ApiError(payload.msg ?? i18n.t('api.requestFailed'), response.status);
    }

    return new ApiError(i18n.t('api.requestFailed'), response.status);
  }

  const text = await response.text();
  return new ApiError(text || '接口请求失败。', response.status);
}

// --- Session expiration handling ---
// Instead of hard-redirecting with window.location.href (which destroys React state),
// we notify a registered handler so AuthProvider can navigate via React Router.
let sessionExpiredHandler: (() => void) | null = null;
let isRedirecting = false;

/**
 * Register a callback to be invoked when a 401 is received.
 * Called by AuthProvider on mount. Pass `null` to unregister.
 */
export function setSessionExpiredHandler(handler: (() => void) | null) {
  sessionExpiredHandler = handler;
  isRedirecting = false; // reset guard when handler changes
}

/**
 * Centralized 401 handling shared by apiRequest and raw fetch callers
 * (streaming/SSE in ai-chat and model test). Guards on DEV_MODE and a
 * redirect-dedupe flag, clears the stored token, and invokes the registered
 * session-expired handler so AuthProvider navigates to /login via React Router.
 * Returns true when the response was acted on as a session-expiring 401.
 */
export function handleUnauthorized(response: Response): boolean {
  if (DEV_MODE || response.status !== 401 || isRedirecting) {
    return false;
  }
  isRedirecting = true;
  clearStoredToken();
  // Notify the registered handler (AuthProvider) to navigate via React Router
  sessionExpiredHandler?.();
  return true;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};

  if (!options.formBody) {
    headers['Content-Type'] = 'application/json';
  }

  if (!options.skipAuth) {
    const token = getStoredToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const body = options.formBody
    ?? (options.body === undefined ? undefined : JSON.stringify(options.body));

  const response = await fetch(buildApiUrl(path, options.query), {
    method: options.method ?? 'GET',
    headers,
    body,
    signal: options.signal,
  });

  if (!response.ok) {
    if (!options.skipAuth && handleUnauthorized(response)) {
      throw new ApiError(i18n.t('api.sessionExpired'), 401);
    }
    throw await parseError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  if (!text.trim()) {
    return undefined as T;
  }

  const payload = JSON.parse(text) as ApiEnvelope<T>;
  if (!payload.success) {
    throw new ApiError(payload.msg || i18n.t('api.requestFailed'), response.status);
  }

  return payload.data;
}
