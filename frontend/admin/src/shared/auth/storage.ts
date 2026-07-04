import type { AuthUser } from './types';

const TOKEN_KEY = 'agentlabkit-token';

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function parseTokenPayload(token: string): AuthUser | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;

    const payload = JSON.parse(atob(parts[1])) as Record<string, unknown>;

    const exp = payload.exp as number | undefined;
    if (exp && Date.now() >= exp * 1000) return null;

    const userId = String(payload.sub ?? '');
    if (!userId) return null;

    const userName = (payload.name as string) ?? null;
    return { userId, userName };
  } catch {
    return null;
  }
}
