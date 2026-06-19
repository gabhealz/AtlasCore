import axios from 'axios';
import { create } from 'zustand';

interface AuthState {
  token: string | null;
  role: string | null;
  email: string | null;
  name: string | null;
  setToken: (token: string | null) => void;
  logout: () => Promise<void>;
}

type JwtPayload = {
  exp?: number;
  role?: string;
  email?: string;
  name?: string;
};

function decodeJwtPayload(token: string): JwtPayload {
  const tokenParts = token.split('.');
  if (tokenParts.length !== 3) return {};
  try {
    const base64 = tokenParts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');
    return JSON.parse(atob(padded)) as JwtPayload;
  } catch {
    return {};
  }
}

export function isTokenExpired(token: string): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload?.exp) return true;
  return payload.exp * 1000 <= Date.now();
}

function getInitialToken(): string | null {
  const stored = localStorage.getItem('token');
  if (!stored || isTokenExpired(stored)) {
    localStorage.removeItem('token');
    return null;
  }
  return stored;
}

function extractFromToken(token: string | null) {
  if (!token || isTokenExpired(token)) return { role: null, email: null, name: null };
  const p = decodeJwtPayload(token);
  return {
    role: p.role ?? null,
    email: p.email ?? null,
    name: p.name ?? null,
  };
}

const initialToken = getInitialToken();
const initialExtracted = extractFromToken(initialToken);

export const useAuthStore = create<AuthState>((set) => ({
  token: initialToken,
  ...initialExtracted,
  setToken: (token) => {
    if (token && !isTokenExpired(token)) {
      localStorage.setItem('token', token);
      set({ token, ...extractFromToken(token) });
    } else {
      localStorage.removeItem('token');
      set({ token: null, role: null, email: null, name: null });
    }
  },
  logout: async () => {
    try {
      await axios.post('/api/v1/auth/logout');
    } catch { /* ignore */ }
    localStorage.removeItem('token');
    set({ token: null, role: null, email: null, name: null });
  },
}));
