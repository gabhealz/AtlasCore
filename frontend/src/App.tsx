import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import OnboardingDetail from './pages/OnboardingDetail';
import NewOnboarding from './pages/NewOnboarding';
import DeliveryPage from './pages/DeliveryPage';
import AuthGuard from './components/AuthGuard';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        
        <Route element={<AuthGuard />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/onboarding/new" element={<NewOnboarding />} />
          <Route path="/onboarding/:id" element={<OnboardingDetail />} />
          <Route path="/onboarding/:id/delivery" element={<DeliveryPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
