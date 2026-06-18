import { useEffect } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { isTokenExpired, useAuthStore } from '../store/auth';

interface AuthGuardProps {
  children?: React.ReactNode;
  allowedRoles?: string[];
}

export default function AuthGuard({ children, allowedRoles }: AuthGuardProps) {
  const token = useAuthStore((state) => state.token);
  const role = useAuthStore((state) => state.role);
  const logout = useAuthStore((state) => state.logout);

  const hasExpiredToken = typeof token === 'string' && isTokenExpired(token);

  useEffect(() => {
    if (hasExpiredToken) {
      void logout();
    }
  }, [hasExpiredToken, logout]);

  if (!token || hasExpiredToken) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && allowedRoles.length > 0 && role && !allowedRoles.includes(role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  if (children) {
    return <>{children}</>;
  }

  return <Outlet />;
}
