import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useLocation,
} from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import OnboardingDetail from './pages/OnboardingDetail';
import NewOnboarding from './pages/NewOnboarding';
import DeliveryPage from './pages/DeliveryPage';
import AuthGuard from './components/AuthGuard';
import AppErrorBoundary from './components/AppErrorBoundary';
import { ErrorBoundary } from './components/ErrorBoundary';
import { OpsDashboard } from './pages/OpsDashboard';
import { OpsClientDetail } from './pages/OpsClientDetail';
import { OpsClientSettings } from './pages/OpsClientSettings';
import { Layout } from './components/Layout';

function AppRoutes() {
  const location = useLocation();

  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route element={<AuthGuard />}>
          <Route path="/dashboard" element={<Layout><Dashboard /></Layout>} />
          <Route path="/onboarding/new" element={<Layout><NewOnboarding /></Layout>} />
          <Route path="/onboarding/:id" element={<Layout><OnboardingDetail /></Layout>} />
          <Route path="/onboarding/:id/delivery" element={<Layout><DeliveryPage /></Layout>} />
          <Route path="/ops" element={<Layout><OpsDashboard /></Layout>} />
          <Route path="/ops/:clientId" element={<Layout><OpsClientDetail /></Layout>} />
          <Route path="/ops/:clientId/settings" element={<Layout><OpsClientSettings /></Layout>} />
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
