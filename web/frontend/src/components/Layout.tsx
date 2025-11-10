/**
 * Main layout component with sidebar
 */
import { Link, Outlet, useLocation } from 'react-router-dom';
import { Home, FolderKanban, ListTodo, Settings } from 'lucide-react';

export function Layout() {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="flex h-screen bg-gray-100 dark:bg-gray-900">
      {/* Sidebar */}
      <aside className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
        <div className="p-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Lazy_Bird
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Phase 1.1</p>
        </div>

        <nav className="px-4 space-y-2">
          <Link
            to="/"
            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
              isActive('/')
                ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-200'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
          >
            <Home size={20} />
            <span>Dashboard</span>
          </Link>

          <Link
            to="/projects"
            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
              isActive('/projects')
                ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-200'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
          >
            <FolderKanban size={20} />
            <span>Projects</span>
          </Link>

          <Link
            to="/queue"
            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
              isActive('/queue')
                ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-200'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
          >
            <ListTodo size={20} />
            <span>Queue</span>
          </Link>

          <Link
            to="/settings"
            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
              isActive('/settings')
                ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-200'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
          >
            <Settings size={20} />
            <span>Settings</span>
          </Link>
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
