import axios from 'axios';
import { create } from 'zustand';

interface AuthState {
  token: string | null;
  role: string | null;
  setToken: (token: string | null) => void;
  logout: () => Promise<void>;
}

type JwtPayload = {
  exp?: number;
  role?: string;
};

function decodeJwtPayload(token: string): JwtPayload {
  const tokenParts = token.split('.');
  if (tokenParts.length !== 3) {
    return {};
  }

  try {
    const base64 = tokenParts[1].replace(/-/g, '+').replace(/_/g, '/');
    const paddedBase64 = base64.padEnd(
      base64.length + ((4 - (base64.length % 4)) % 4),
      '=',
    );
    const decodedPayload = atob(paddedBase64);
    return JSON.parse(decodedPayload) as JwtPayload;
  } catch {
    return {};
  }
}

export function isTokenExpired(token: string): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload?.exp) {
    return true;
  }

  return payload.exp * 1000 <= Date.now();
}

function getInitialToken(): string | null {
  const storedToken = localStorage.getItem('token');
  if (!storedToken) {
    return null;
  }

  if (isTokenExpired(storedToken)) {
    localStorage.removeItem('token');
    return null;
  }

  return storedToken;
}

function getInitialRole(): string | null {
  const storedToken = localStorage.getItem('token');
  if (!storedToken || isTokenExpired(storedToken)) {
    return null;
  }
  return decodeJwtPayload(storedToken).role ?? null;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: getInitialToken(),
  role: getInitialRole(),
  setToken: (token) => {
    if (token && !isTokenExpired(token)) {
      localStorage.setItem('token', token);
      const role = decodeJwtPayload(token).role ?? null;
      set({ token, role });
    } else {
      localStorage.removeItem('token');
      set({ token: null, role: null });
    }
  },
  logout: async () => {
    try {
      await axios.post('/api/v1/auth/logout');
    } catch { /* ignore errors on logout */ }
    localStorage.removeItem('token');
    set({ token: null, role: null });
  },
}));
