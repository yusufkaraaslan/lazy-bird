/**
 * SettingsTab Page
 *
 * Settings and management hub
 * Contains: Projects, Queue, Services, and System Settings
 */

import { Link } from 'react-router-dom';
import { Folder, ListTodo, Server, Settings as SettingsIcon, ChevronRight } from 'lucide-react';

interface SettingSection {
  id: string;
  title: string;
  description: string;
  icon: typeof Folder;
  path: string;
}

const SETTING_SECTIONS: SettingSection[] = [
  {
    id: 'projects',
    title: 'Projects',
    description: 'Manage your projects and repositories',
    icon: Folder,
    path: '/projects',
  },
  {
    id: 'queue',
    title: 'Task Queue',
    description: 'View and manage queued tasks',
    icon: ListTodo,
    path: '/queue',
  },
  {
    id: 'services',
    title: 'Services',
    description: 'Configure external services and integrations',
    icon: Server,
    path: '/services',
  },
  {
    id: 'settings',
    title: 'System Settings',
    description: 'General system configuration and preferences',
    icon: SettingsIcon,
    path: '/settings',
  },
];

export function SettingsTab() {
  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              Settings & Management
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Configure your Lazy Bird installation, manage projects, and view system settings
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {SETTING_SECTIONS.map((section) => {
              const Icon = section.icon;
              return (
                <Link
                  key={section.id}
                  to={section.path}
                  className="group block p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600 hover:shadow-card-hover transition-all duration-200"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      <div className="p-3 rounded-lg bg-gradient-primary text-white shadow-glow-sm">
                        <Icon className="w-6 h-6" />
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                          {section.title}
                        </h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {section.description}
                        </p>
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-primary-500 group-hover:translate-x-1 transition-all" />
                  </div>
                </Link>
              );
            })}
          </div>

          {/* Theme Toggle Section */}
          <div className="mt-8 p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Appearance
            </h3>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Theme Mode
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Toggle between light and dark mode
                </p>
              </div>
              {/* Theme toggle will be added in a future component */}
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Toggle coming soon
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
