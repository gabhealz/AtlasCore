import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import AuthGuard from './components/AuthGuard';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Layout } from './components/Layout';
import Dashboard from './pages/Dashboard';
import DeliveryPage from './pages/DeliveryPage';
import Login from './pages/Login';
import AcceptInvite from './pages/AcceptInvite';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import NewOnboarding from './pages/NewOnboarding';
import OnboardingDetail from './pages/OnboardingDetail';
import { AdminUsers } from './pages/AdminUsers';
import { OpsClientDetail } from './pages/OpsClientDetail';
import { OpsClientSettings } from './pages/OpsClientSettings';
import { OpsDashboard } from './pages/OpsDashboard';
import { SeoResearch } from './pages/SeoResearch';

function AppRoutes() {
  return (
    <ErrorBoundary>
      <Routes>
        {/* Public auth routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/accept-invite" element={<AcceptInvite />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        {/* Protected routes */}
        <Route element={<AuthGuard />}>
          <Route path="/dashboard" element={<Layout><Dashboard /></Layout>} />
          <Route path="/onboarding/new" element={<Layout><NewOnboarding /></Layout>} />
          <Route path="/onboarding/:id" element={<Layout><OnboardingDetail /></Layout>} />
          <Route path="/onboarding/:id/delivery" element={<Layout><DeliveryPage /></Layout>} />
          <Route path="/ops" element={<Layout><OpsDashboard /></Layout>} />
          <Route path="/ops/:clientId" element={<Layout><OpsClientDetail /></Layout>} />
          <Route path="/ops/:clientId/settings" element={<Layout><OpsClientSettings /></Layout>} />
          <Route path="/seo" element={<Layout><SeoResearch /></Layout>} />
          <Route path="/admin/users" element={<AuthGuard allowedRoles={['admin']}><Layout><AdminUsers /></Layout></AuthGuard>} />
        </Route>

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </ErrorBoundary>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
