/**
 * ViewSelector Component
 *
 * Mid-level navigation: Overall, Project, Agent views
 * Shows project selector when in Project view
 */

import { motion } from 'framer-motion';
import { Globe, Folder, Bot, ChevronDown, Search, AlertCircle } from 'lucide-react';
import { useDashboardStore } from '../store';
import type { ViewType } from '../store';
import { useThemeStore } from '../store';
import { useState, useEffect } from 'react';
import { projectsApi } from '../lib/api';
import type { Project } from '../types/api';

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

export function ViewSelector() {
  const currentView = useDashboardStore((state) => state.currentView);
  const setCurrentView = useDashboardStore((state) => state.setCurrentView);
  const selectedProjectId = useDashboardStore((state) => state.selectedProjectId);
  const setSelectedProjectId = useDashboardStore((state) => state.setSelectedProjectId);
  const animationsEnabled = useThemeStore((state) => state.animationsEnabled);

  const [projectDropdownOpen, setProjectDropdownOpen] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Fetch projects from API
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const response = await projectsApi.list();
        const allProjects = response.data.projects || [];
        setProjects(allProjects.filter((p: Project) => p.enabled));
        setError(null);

        // If no project is selected, select the first enabled project
        if (!selectedProjectId && allProjects.length > 0) {
          const firstEnabled = allProjects.find((p: Project) => p.enabled);
          if (firstEnabled) {
            setSelectedProjectId(firstEnabled.id);
          }
        }
      } catch (err: any) {
        console.error('Failed to fetch projects:', err);
        setError(err.message || 'Failed to load projects');
      } finally {
        setLoading(false);
      }
    };

    fetchProjects();
    const interval = setInterval(fetchProjects, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [selectedProjectId, setSelectedProjectId]);

  // Filter projects based on search query
  const filteredProjects = projects.filter(project =>
    project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    project.type.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const selectedProject = projects.find(p => p.id === selectedProjectId) || projects[0];

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
          {loading ? (
            <div className="flex items-center gap-2 px-3 py-1.5">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-500"></div>
              <span className="text-sm text-gray-600 dark:text-gray-400">Loading projects...</span>
            </div>
          ) : error ? (
            <div className="flex items-center gap-2 px-3 py-1.5 text-sm text-red-600 dark:text-red-400">
              <AlertCircle className="w-4 h-4" />
              <span>{error}</span>
            </div>
          ) : projects.length === 0 ? (
            <div className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-500 dark:text-gray-400">
              <Folder className="w-4 h-4" />
              <span>No projects available</span>
            </div>
          ) : (
            <>
              <button
                onClick={() => setProjectDropdownOpen(!projectDropdownOpen)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-white dark:bg-gray-700 text-sm font-medium text-gray-900 dark:text-gray-100 shadow-sm hover:shadow transition-shadow duration-200"
              >
                <Folder className="w-4 h-4 text-primary-500" />
                <span>{selectedProject?.name || 'Select Project'}</span>
                <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${projectDropdownOpen ? 'rotate-180' : ''}`} />
              </button>

              {/* Dropdown */}
              {projectDropdownOpen && (
                <>
                  {/* Backdrop */}
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => {
                      setProjectDropdownOpen(false);
                      setSearchQuery('');
                    }}
                  />

                  {/* Menu */}
                  <motion.div
                    initial={animationsEnabled ? { opacity: 0, y: -10 } : {}}
                    animate={animationsEnabled ? { opacity: 1, y: 0 } : {}}
                    className="absolute right-0 mt-2 w-64 rounded-lg bg-white dark:bg-gray-700 shadow-lg border border-gray-200 dark:border-gray-600 z-20"
                  >
                    {/* Search Input */}
                    <div className="p-2 border-b border-gray-200 dark:border-gray-600">
                      <div className="relative">
                        <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-gray-400" />
                        <input
                          type="text"
                          placeholder="Search projects..."
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          className="w-full pl-8 pr-3 py-2 text-sm bg-gray-50 dark:bg-gray-600 border border-gray-200 dark:border-gray-500 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 dark:text-gray-100 placeholder-gray-400"
                          onClick={(e) => e.stopPropagation()}
                          autoFocus
                        />
                      </div>
                    </div>

                    {/* Projects List */}
                    <div className="py-1 max-h-64 overflow-y-auto">
                      {filteredProjects.length === 0 ? (
                        <div className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 text-center">
                          No projects found
                        </div>
                      ) : (
                        filteredProjects.map((project) => (
                          <button
                            key={project.id}
                            onClick={() => {
                              setSelectedProjectId(project.id);
                              setProjectDropdownOpen(false);
                              setSearchQuery('');
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
                                {project.type}
                              </div>
                            </div>
                          </button>
                        ))
                      )}
                    </div>
                  </motion.div>
                </>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
