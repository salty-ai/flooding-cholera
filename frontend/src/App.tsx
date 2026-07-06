import { useState, Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastProvider } from './components/common/Toast';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { useAuthStore } from './store/authStore';
import LoginScreen from './components/Auth/LoginScreen';
import MainLayout from './components/Layout/MainLayout';

// Lazy load heavy components
const ReportsView = lazy(() => import('./components/Dashboard/ReportsView'));
const AlertsPanel = lazy(() => import('./components/Alerts/AlertsPanel'));
const SatellitePanel = lazy(() => import('./components/Satellite/SatellitePanel'));
const DataUpload = lazy(() => import('./components/Upload/DataUpload'));
const LGAReportPage = lazy(() => import('./components/LGADetail/LGAReportPage'));
const CorrelationView = lazy(() => import('./components/Analytics/CorrelationView'));

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
      staleTime: 60 * 1000,
    },
  },
});

export type TabId = 'dashboard' | 'map' | 'reports' | 'alerts' | 'satellite' | 'settings' | 'correlation';

export function LoadingFallback() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
    </div>
  );
}

// Dashboard view with KPIs, Map, and Charts
const DashboardView = lazy(() => import('./components/Dashboard/DashboardView'));
const MapOnlyView = lazy(() => import('./components/Dashboard/MapOnlyView'));

// Map route to tab
function routeToTab(pathname: string): TabId {
  if (pathname === '/map') return 'map';
  if (pathname === '/reports') return 'reports';
  if (pathname === '/alerts') return 'alerts';
  if (pathname === '/satellite') return 'satellite';
  if (pathname === '/settings') return 'settings';
  if (pathname === '/correlation') return 'correlation';
  return 'dashboard';
}

// Map tab to route
function tabToRoute(tab: TabId): string {
  if (tab === 'dashboard') return '/';
  return `/${tab}`;
}

function MainAppContent() {
  const location = useLocation();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabId>(() => routeToTab(location.pathname));
  const { isAuthenticated, login } = useAuthStore();

  // Handle tab change with navigation
  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    navigate(tabToRoute(tab));
  };

  // Show login screen if not authenticated
  if (!isAuthenticated) {
    return <LoginScreen onLogin={login} />;
  }

  return (
    <Routes>
      {/* LGA Report Page - Full screen, outside MainLayout */}
      <Route
        path="/lga/:lgaId"
        element={
          <Suspense fallback={<LoadingFallback />}>
            <LGAReportPage />
          </Suspense>
        }
      />
      
      {/* Main app routes - inside MainLayout */}
      <Route
        path="*"
        element={
          <MainLayout activeTab={activeTab} onTabChange={handleTabChange}>
            <ErrorBoundary>
              <Suspense fallback={<LoadingFallback />}>
                <Routes>
                  <Route path="/" element={<DashboardView />} />
                  <Route path="/map" element={<MapOnlyView />} />
                  <Route path="/reports" element={<ReportsView />} />
                  <Route path="/alerts" element={<AlertsPanel />} />
                  <Route path="/satellite" element={<SatellitePanel />} />
                  <Route path="/settings" element={<DataUpload />} />
                  <Route path="/correlation" element={<CorrelationView />} />
                </Routes>
              </Suspense>
            </ErrorBoundary>
          </MainLayout>
        }
      />
    </Routes>
  );
}

function AppContent() {
  return (
    <BrowserRouter>
      <MainAppContent />
    </BrowserRouter>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <AppContent />
      </ErrorBoundary>
      <ToastProvider />
    </QueryClientProvider>
  );
}
