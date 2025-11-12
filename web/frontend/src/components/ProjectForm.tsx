/**
 * Project form component for adding/editing projects
 */
import { useState, useEffect } from 'react';
import type { Project, ProjectCreate } from '../types/api';

interface ProjectFormProps {
  project?: Project | null;
  onClose: () => void;
  onSave: (data: ProjectCreate) => Promise<void>;
}

export function ProjectForm({ project, onClose, onSave }: ProjectFormProps) {
  const [formData, setFormData] = useState<ProjectCreate>({
    name: '',
    type: 'godot',
    path: '',
    repository: '',
    git_platform: 'github',
    test_command: '',
    build_command: '',
    enabled: true,
  });

  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Populate form when editing
  useEffect(() => {
    if (project) {
      setFormData({
        name: project.name,
        type: project.type,
        path: project.path,
        repository: project.repository,
        git_platform: project.git_platform,
        test_command: project.test_command || '',
        build_command: project.build_command || '',
        enabled: project.enabled,
      });
    }
  }, [project]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSaving(true);

    try {
      await onSave(formData);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save project');
    } finally {
      setIsSaving(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    setFormData((prev: ProjectCreate) => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }));
  };

  return (
    <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 p-4 rounded-lg">
              {error}
            </div>
          )}

          {/* Name */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              Name
            </label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              placeholder="My Awesome Project"
            />
          </div>

          {/* Two columns: Type and Platform */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="type" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Type
              </label>
              <select
                id="type"
                name="type"
                value={formData.type}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="godot">Godot</option>
                <option value="unity">Unity</option>
                <option value="python">Python</option>
                <option value="rust">Rust</option>
                <option value="nodejs">Node.js</option>
                <option value="react">React</option>
                <option value="django">Django</option>
                <option value="flask">Flask</option>
                <option value="custom">Custom</option>
              </select>
            </div>

            <div>
              <label htmlFor="git_platform" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Platform
              </label>
              <select
                id="git_platform"
                name="git_platform"
                value={formData.git_platform}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="github">GitHub</option>
                <option value="gitlab">GitLab</option>
              </select>
            </div>
          </div>

          {/* Path */}
          <div>
            <label htmlFor="path" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              Path
            </label>
            <input
              type="text"
              id="path"
              name="path"
              value={formData.path}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono"
              placeholder="/path/to/project"
            />
          </div>

          {/* Repository URL */}
          <div>
            <label htmlFor="repository" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
              Repository
            </label>
            <input
              type="url"
              id="repository"
              name="repository"
              value={formData.repository}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono"
              placeholder="https://github.com/username/repo"
            />
          </div>

          {/* Optional Commands - Collapsible Section */}
          <details className="group">
            <summary className="cursor-pointer text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white py-2">
              Commands (optional)
            </summary>
            <div className="space-y-3 pt-2">
              <div>
                <label htmlFor="test_command" className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">
                  Test
                </label>
                <input
                  type="text"
                  id="test_command"
                  name="test_command"
                  value={formData.test_command}
                  onChange={handleChange}
                  className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono"
                  placeholder="npm test"
                />
              </div>

              <div>
                <label htmlFor="build_command" className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">
                  Build
                </label>
                <input
                  type="text"
                  id="build_command"
                  name="build_command"
                  value={formData.build_command}
                  onChange={handleChange}
                  className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono"
                  placeholder="npm run build"
                />
              </div>
            </div>
          </details>

          {/* Enabled toggle */}
          <div className="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-700/50 rounded-md">
            <label htmlFor="enabled" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Enable project
            </label>
            <input
              type="checkbox"
              id="enabled"
              name="enabled"
              checked={formData.enabled}
              onChange={handleChange}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
          </div>

          {/* Buttons */}
          <div className="flex justify-end gap-2 pt-4 mt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSaving ? 'Saving...' : project ? 'Save Changes' : 'Create Project'}
            </button>
          </div>
    </form>
  );
}
