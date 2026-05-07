import { create } from 'zustand';

interface AuthState {
  token: string | null;
  setToken: (token: string | null) => void;
  logout: () => void;
}

type JwtPayload = {
  exp?: number;
};

function decodeJwtPayload(token: string): JwtPayload | null {
  const tokenParts = token.split('.');
  if (tokenParts.length !== 3) {
    return null;
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
    return null;
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

export const useAuthStore = create<AuthState>((set) => ({
  token: getInitialToken(),
  setToken: (token) => {
    if (token && !isTokenExpired(token)) {
      localStorage.setItem('token', token);
      set({ token });
    } else {
      localStorage.removeItem('token');
      set({ token: null });
    }
  },
  logout: () => {
    localStorage.removeItem('token');
    set({ token: null });
  },
}));
