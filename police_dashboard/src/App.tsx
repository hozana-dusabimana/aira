import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/layout/Layout';
import { useAuth } from './context/AuthContext';
import Analytics from './pages/Analytics';
import Citizens from './pages/Citizens';
import Dashboard from './pages/Dashboard';
import IncidentDetails from './pages/IncidentDetails';
import IncidentsList from './pages/IncidentsList';
import Landing from './pages/Landing';
import Login from './pages/Login';
import MapView from './pages/MapView';
import Officers from './pages/Officers';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import Spam from './pages/Spam';
import SystemStatusPage from './pages/SystemStatus';

export default function App() {
  const { user, loading } = useAuth();

  if (loading) return <div style={{ padding: 24 }}>Loading...</div>;

  if (!user) {
    return (
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/incidents" element={<IncidentsList />} />
        <Route path="/incidents/:id" element={<IncidentDetails />} />
        <Route path="/spam" element={<Spam />} />
        <Route path="/map" element={<MapView />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/officers" element={<Officers />} />
        <Route path="/citizens" element={<Citizens />} />
        <Route path="/status" element={<SystemStatusPage />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
