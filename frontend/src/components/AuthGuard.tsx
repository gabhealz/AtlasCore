import { useEffect } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { isTokenExpired, useAuthStore } from '../store/auth';

export default function AuthGuard() {
  const token = useAuthStore((state) => state.token);
  const logout = useAuthStore((state) => state.logout);

  const hasExpiredToken = typeof token === 'string' && isTokenExpired(token);

  useEffect(() => {
    if (hasExpiredToken) {
      logout();
    }
  }, [hasExpiredToken, logout]);

  if (!token || hasExpiredToken) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
