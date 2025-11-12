/**
 * Project form modal for adding/editing projects
 */
import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
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

  return createPortal(
    <div
      className="fixed top-0 left-0 right-0 bottom-0 flex items-center justify-center p-4"
      style={{
        zIndex: 9999,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
      }}
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl w-full overflow-y-auto"
        style={{ maxWidth: '600px', maxHeight: '90vh' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            {project ? 'Edit Project' : 'Add Project'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {error && (
            <div className="bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 p-4 rounded-lg">
              {error}
            </div>
          )}

          {/* Name */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Project Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              placeholder="My Awesome Project"
            />
          </div>

          {/* Type (Framework) */}
          <div>
            <label htmlFor="type" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Project Type <span className="text-red-500">*</span>
            </label>
            <select
              id="type"
              name="type"
              value={formData.type}
              onChange={handleChange}
              required
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
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

          {/* Path */}
          <div>
            <label htmlFor="path" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Project Path <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="path"
              name="path"
              value={formData.path}
              onChange={handleChange}
              required
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              placeholder="/path/to/project"
            />
          </div>

          {/* Repository URL */}
          <div>
            <label htmlFor="repository" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Repository URL <span className="text-red-500">*</span>
            </label>
            <input
              type="url"
              id="repository"
              name="repository"
              value={formData.repository}
              onChange={handleChange}
              required
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              placeholder="https://github.com/username/repo"
            />
          </div>

          {/* Git Platform */}
          <div>
            <label htmlFor="git_platform" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Git Platform <span className="text-red-500">*</span>
            </label>
            <select
              id="git_platform"
              name="git_platform"
              value={formData.git_platform}
              onChange={handleChange}
              required
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="github">GitHub</option>
              <option value="gitlab">GitLab</option>
            </select>
          </div>

          {/* Test Command */}
          <div>
            <label htmlFor="test_command" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Test Command
            </label>
            <input
              type="text"
              id="test_command"
              name="test_command"
              value={formData.test_command}
              onChange={handleChange}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              placeholder="npm test"
            />
          </div>

          {/* Build Command */}
          <div>
            <label htmlFor="build_command" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Build Command
            </label>
            <input
              type="text"
              id="build_command"
              name="build_command"
              value={formData.build_command}
              onChange={handleChange}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              placeholder="npm run build"
            />
          </div>

          {/* Enabled checkbox */}
          <div className="flex items-center">
            <input
              type="checkbox"
              id="enabled"
              name="enabled"
              checked={formData.enabled}
              onChange={handleChange}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <label htmlFor="enabled" className="ml-2 text-sm font-medium text-gray-700 dark:text-gray-300">
              Enable project
            </label>
          </div>

          {/* Buttons */}
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSaving ? 'Saving...' : project ? 'Update Project' : 'Add Project'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}
