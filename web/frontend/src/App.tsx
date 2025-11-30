/**
 * Main App component with routing
 */
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { TabNavigation } from './components/TabNavigation';
import { SettingsPageWrapper } from './components/SettingsPageWrapper';
import { DashboardTab } from './pages/DashboardTab';
import { AnalyticsTab } from './pages/AnalyticsTab';
import { SettingsTab } from './pages/SettingsTab';
import { ProjectsPage } from './pages/ProjectsPage';
import { ProjectFormPage } from './pages/ProjectFormPage';
import { QueuePage } from './pages/QueuePage';
import { ServicesPage } from './pages/ServicesPage';
import { ServiceFormPage } from './pages/ServiceFormPage';
import { SettingsPage } from './pages/SettingsPage';
import { useDashboardStore } from './store';
import { useThemeStore } from './store';
import { useEffect } from 'react';

function MainLayout() {
  const activeTab = useDashboardStore((state) => state.activeTab);
  const setActiveTab = useDashboardStore((state) => state.setActiveTab);
  const location = useLocation();

  // Auto-switch to Settings tab when on settings routes
  useEffect(() => {
    if (
      location.pathname.startsWith('/projects') ||
      location.pathname.startsWith('/queue') ||
      location.pathname.startsWith('/services') ||
      location.pathname.startsWith('/settings')
    ) {
      setActiveTab('settings');
    }
  }, [location.pathname, setActiveTab]);

  // Check if we're on a settings sub-route
  const isOnSettingsRoute = location.pathname.match(/^\/(projects|queue|services|settings)/);

  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900">
      <TabNavigation />
      <div className="flex-1 overflow-hidden">
        {isOnSettingsRoute ? (
          // Show settings routes
          <Routes>
            <Route
              path="projects"
              element={
                <SettingsPageWrapper>
                  <ProjectsPage />
                </SettingsPageWrapper>
              }
            />
            <Route
              path="projects/add"
              element={
                <SettingsPageWrapper>
                  <ProjectFormPage />
                </SettingsPageWrapper>
              }
            />
            <Route
              path="projects/:id/edit"
              element={
                <SettingsPageWrapper>
                  <ProjectFormPage />
                </SettingsPageWrapper>
              }
            />
            <Route
              path="queue"
              element={
                <SettingsPageWrapper>
                  <QueuePage />
                </SettingsPageWrapper>
              }
            />
            <Route
              path="services"
              element={
                <SettingsPageWrapper>
                  <ServicesPage />
                </SettingsPageWrapper>
              }
            />
            <Route
              path="services/add"
              element={
                <SettingsPageWrapper>
                  <ServiceFormPage />
                </SettingsPageWrapper>
              }
            />
            <Route
              path="services/:name/edit"
              element={
                <SettingsPageWrapper>
                  <ServiceFormPage />
                </SettingsPageWrapper>
              }
            />
            <Route
              path="settings"
              element={
                <SettingsPageWrapper>
                  <SettingsPage />
                </SettingsPageWrapper>
              }
            />
          </Routes>
        ) : (
          // Show main tab content
          <>
            {activeTab === 'dashboard' && <DashboardTab />}
            {activeTab === 'analytics' && <AnalyticsTab />}
            {activeTab === 'settings' && <SettingsTab />}
          </>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const mode = useThemeStore((state) => state.mode);
  const setMode = useThemeStore((state) => state.setMode);

  // Apply theme on mount
  useEffect(() => {
    setMode(mode);
  }, []);

  return (
    <BrowserRouter>
      <MainLayout />
    </BrowserRouter>
  );
}
