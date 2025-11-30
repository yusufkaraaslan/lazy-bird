/**
 * ViewSelector Component
 *
 * Mid-level navigation: Overall, Project, Agent views
 * Shows project selector when in Project view
 */

import { motion } from 'framer-motion';
import { Globe, Folder, Bot, ChevronDown } from 'lucide-react';
import { useDashboardStore } from '../store';
import type { ViewType } from '../store';
import { useThemeStore } from '../store';
import { useState } from 'react';

interface View {
  id: ViewType;
  label: string;
  icon: typeof Globe;
  description: string;
}

const VIEWS: View[] = [
  {
    id: 'overall',
    label: 'Overall',
    icon: Globe,
    description: 'System-wide overview'
  },
  {
    id: 'project',
    label: 'Project',
    icon: Folder,
    description: 'Project-specific view'
  },
  {
    id: 'agent',
    label: 'Agent',
    icon: Bot,
    description: 'Individual agent view'
  },
];

// Mock projects data - will be replaced with API data
const MOCK_PROJECTS = [
  { id: 'proj-1', name: 'Lazy Bird', status: 'active' },
  { id: 'proj-2', name: 'Web UI', status: 'active' },
  { id: 'proj-3', name: 'API Server', status: 'active' },
];

export function ViewSelector() {
  const currentView = useDashboardStore((state) => state.currentView);
  const setCurrentView = useDashboardStore((state) => state.setCurrentView);
  const selectedProjectId = useDashboardStore((state) => state.selectedProjectId);
  const setSelectedProjectId = useDashboardStore((state) => state.setSelectedProjectId);
  const animationsEnabled = useThemeStore((state) => state.animationsEnabled);
  const [projectDropdownOpen, setProjectDropdownOpen] = useState(false);

  const selectedProject = MOCK_PROJECTS.find(p => p.id === selectedProjectId) || MOCK_PROJECTS[0];

  return (
    <div className="flex items-center justify-between px-6 py-3 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
      {/* View Selector Buttons */}
      <div className="flex items-center gap-2">
        {VIEWS.map((view) => {
          const Icon = view.icon;
          const isActive = currentView === view.id;

          return (
            <button
              key={view.id}
              onClick={() => setCurrentView(view.id)}
              className={`
                flex items-center gap-2 px-3 py-1.5 rounded-md
                text-xs font-medium transition-all duration-200
                ${
                  isActive
                    ? 'bg-white dark:bg-gray-700 text-primary-600 dark:text-primary-400 shadow-sm'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-white/50 dark:hover:bg-gray-700/50'
                }
              `}
              title={view.description}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{view.label}</span>
            </button>
          );
        })}
      </div>

      {/* Project Selector (only visible in Project view) */}
      {currentView === 'project' && (
        <div className="relative">
          <button
            onClick={() => setProjectDropdownOpen(!projectDropdownOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-white dark:bg-gray-700 text-sm font-medium text-gray-900 dark:text-gray-100 shadow-sm hover:shadow transition-shadow duration-200"
          >
            <Folder className="w-4 h-4 text-primary-500" />
            <span>{selectedProject.name}</span>
            <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${projectDropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          {/* Dropdown */}
          {projectDropdownOpen && (
            <>
              {/* Backdrop */}
              <div
                className="fixed inset-0 z-10"
                onClick={() => setProjectDropdownOpen(false)}
              />

              {/* Menu */}
              <motion.div
                initial={animationsEnabled ? { opacity: 0, y: -10 } : {}}
                animate={animationsEnabled ? { opacity: 1, y: 0 } : {}}
                className="absolute right-0 mt-2 w-56 rounded-lg bg-white dark:bg-gray-700 shadow-lg border border-gray-200 dark:border-gray-600 z-20"
              >
                <div className="py-1">
                  {MOCK_PROJECTS.map((project) => (
                    <button
                      key={project.id}
                      onClick={() => {
                        setSelectedProjectId(project.id);
                        setProjectDropdownOpen(false);
                      }}
                      className={`
                        w-full flex items-center gap-3 px-4 py-2 text-sm
                        transition-colors duration-150
                        ${
                          project.id === selectedProjectId
                            ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'
                        }
                      `}
                    >
                      <Folder className="w-4 h-4" />
                      <div className="flex-1 text-left">
                        <div className="font-medium">{project.name}</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {project.status}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </motion.div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
