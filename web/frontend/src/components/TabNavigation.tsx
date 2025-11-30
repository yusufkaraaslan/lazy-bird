/**
 * TabNavigation Component
 *
 * Top-level navigation with 3 tabs: Dashboard, Analytics, Settings
 */

import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { LayoutDashboard, BarChart3, Settings } from 'lucide-react';
import { useDashboardStore } from '../store';
import type { TabType } from '../store';
import { useThemeStore } from '../store';

interface Tab {
  id: TabType;
  label: string;
  icon: typeof LayoutDashboard;
}

const TABS: Tab[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function TabNavigation() {
  const activeTab = useDashboardStore((state) => state.activeTab);
  const setActiveTab = useDashboardStore((state) => state.setActiveTab);
  const animationsEnabled = useThemeStore((state) => state.animationsEnabled);
  const navigate = useNavigate();

  const handleTabClick = (tabId: TabType) => {
    setActiveTab(tabId);
    // Navigate to root to show the tab content (not a sub-route)
    navigate('/');
  };

  return (
    <nav className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
      <div className="flex space-x-1 px-6">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => handleTabClick(tab.id)}
              className={`
                relative flex items-center gap-2 px-4 py-3
                text-sm font-medium transition-colors duration-200
                ${
                  isActive
                    ? 'text-primary-600 dark:text-primary-400'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                }
              `}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>

              {/* Active indicator */}
              {isActive && animationsEnabled && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-primary"
                  transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                />
              )}

              {isActive && !animationsEnabled && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-primary" />
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
