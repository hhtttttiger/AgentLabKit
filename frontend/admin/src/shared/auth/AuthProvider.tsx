import { createContext, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import type { AuthUser } from './types';
import { login as loginApi } from './api';
import {
  clearStoredToken,
  getStoredToken,
  parseTokenPayload,
  setStoredToken,
} from './storage';
import { setSessionExpiredHandler } from '@/shared/api/client';
import { queryClient } from '@/shared/api/queryClient';

export const DEV_MODE = import.meta.env.VITE_DEV_MODE === 'true';

const DEV_USER: AuthUser = { userId: 'dev', userName: 'Dev User' };
const DEV_TOKEN = `dev.${btoa(JSON.stringify({ sub: 'dev', name: 'Dev User', exp: Math.floor(Date.now() / 1000) + 86400 }))}.dev`;

export type AuthContextValue = {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (username: string, password: string, provider?: string) => Promise<void>;
  logout: () => void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);

function loadInitialState(): { token: string | null; user: AuthUser | null } {
  if (DEV_MODE) {
    return { token: DEV_TOKEN, user: DEV_USER };
  }

  const token = getStoredToken();
  if (!token) return { token: null, user: null };

  const user = parseTokenPayload(token);
  if (!user) {
    clearStoredToken();
    return { token: null, user: null };
  }

  return { token, user };
}

function getTokenExpiresAt(token: string): number | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1])) as Record<string, unknown>;
    return typeof payload.exp === 'number' ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState(loadInitialState);
  const navigate = useNavigate();

  const logout = useCallback(() => {
    queryClient.clear();
    clearStoredToken();
    setState({ token: null, user: null });
  }, []);

  const logoutRef = useRef(logout);
  logoutRef.current = logout;

  // Register 401 handler: navigate via React Router instead of window.location.href
  useEffect(() => {
    const handler = () => {
      const currentPath = window.location.pathname;
      try {
        logout();
        navigate('/login', { state: { from: currentPath }, replace: true });
      } finally {
        // Always reset the redirect guard so future 401s can trigger again
        setTimeout(() => {
          setSessionExpiredHandler(handler);
        }, 0);
      }
    };
    setSessionExpiredHandler(handler);
    return () => setSessionExpiredHandler(null);
  }, [logout, navigate]);

  // Proactive token expiration check: redirect to login when JWT exp is reached
  useEffect(() => {
    if (!state.token || DEV_MODE) return;

    const expiresAt = getTokenExpiresAt(state.token);
    if (!expiresAt) return;

    const timeUntilExpiry = expiresAt - Date.now();
    if (timeUntilExpiry <= 0) {
      const currentPath = window.location.pathname;
      queryClient.clear();
      logoutRef.current();
      navigate('/login', { state: { from: currentPath }, replace: true });
      return;
    }

    const timer = setTimeout(() => {
      const currentPath = window.location.pathname;
      try {
        queryClient.clear();
        logoutRef.current();
        navigate('/login', { state: { from: currentPath }, replace: true });
      } catch (error) {
        console.error('Failed to redirect on token expiry:', error);
        // Fallback: force reload to clear state
        window.location.href = '/login';
      }
    }, timeUntilExpiry);

    return () => clearTimeout(timer);
  }, [state.token, navigate]);

  const login = useCallback(async (username: string, password: string, provider?: string) => {
    const response = await loginApi({ username, password, provider });
    const user = parseTokenPayload(response.accessToken);
    setStoredToken(response.accessToken);
    setState({ token: response.accessToken, user });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token: state.token,
      user: state.user,
      isAuthenticated: state.token !== null,
      login,
      logout,
    }),
    [state, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
