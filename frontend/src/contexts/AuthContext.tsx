import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { api } from '../services/api';

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing token
    const token = api.getToken();
    const storedUser = localStorage.getItem('atlas_user');
    if (token && storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        api.setToken(null);
        localStorage.removeItem('atlas_user');
      }
    }
    setLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const data = await api.login(email, password);
    api.setToken(data.access_token);
    localStorage.setItem('atlas_user', JSON.stringify(data.user));
    setUser(data.user);
  };

  const register = async (email: string, password: string, fullName: string) => {
    const data = await api.register(email, password, fullName);
    api.setToken(data.access_token);
    localStorage.setItem('atlas_user', JSON.stringify(data.user));
    setUser(data.user);
  };

  const logout = () => {
    api.setToken(null);
    localStorage.removeItem('atlas_user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
