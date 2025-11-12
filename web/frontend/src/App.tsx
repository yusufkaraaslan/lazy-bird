/**
 * Main App component with routing
 */
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { ProjectFormPage } from './pages/ProjectFormPage';
import { QueuePage } from './pages/QueuePage';
import { ServicesPage } from './pages/ServicesPage';
import { ServiceFormPage } from './pages/ServiceFormPage';
import { SettingsPage } from './pages/SettingsPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="projects/add" element={<ProjectFormPage />} />
          <Route path="projects/:id/edit" element={<ProjectFormPage />} />
          <Route path="queue" element={<QueuePage />} />
          <Route path="services" element={<ServicesPage />} />
          <Route path="services/add" element={<ServiceFormPage />} />
          <Route path="services/:name/edit" element={<ServiceFormPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
