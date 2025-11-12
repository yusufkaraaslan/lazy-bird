/**
 * Projects page - Manage all projects
 */
import { useState } from 'react';
import { useProjects, useCreateProject, useUpdateProject, useDeleteProject, useToggleProject } from '../hooks/useProjects';
import { Plus, Edit2, Trash2, Power, AlertCircle } from 'lucide-react';
import type { Project } from '../types/api';
import { ProjectForm } from '../components/ProjectForm';

export function ProjectsPage() {
  const { data: projects, isLoading, error } = useProjects();
  const createProject = useCreateProject();
  const updateProject = useUpdateProject();
  const deleteProject = useDeleteProject();
  const toggleProject = useToggleProject();

  const [showAddForm, setShowAddForm] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="text-gray-600 dark:text-gray-400">Loading projects...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 p-4 rounded-lg">
          <div className="flex items-center gap-2">
            <AlertCircle size={20} />
            <span>Failed to load projects</span>
          </div>
        </div>
      </div>
    );
  }

  const handleToggle = async (id: string, enabled: boolean) => {
    try {
      await toggleProject.mutateAsync({ id, enabled: !enabled });
    } catch (err) {
      console.error('Toggle failed:', err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this project?')) return;

    try {
      await deleteProject.mutateAsync(id);
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  return (
    <>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto p-6 lg:p-8">
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Projects</h1>
              <p className="text-gray-600 dark:text-gray-400">Manage your development projects</p>
            </div>
            <button
              onClick={() => setShowAddForm(true)}
              className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm hover:shadow-md"
            >
              <Plus size={20} />
              <span>Add Project</span>
            </button>
          </div>

        {/* Projects List */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {projects && projects.length === 0 && (
            <div className="col-span-2 text-center py-16 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
              <p className="text-gray-600 dark:text-gray-400 mb-6 text-lg">No projects configured yet</p>
              <button
                onClick={() => setShowAddForm(true)}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm hover:shadow-md"
              >
                Add Your First Project
              </button>
            </div>
          )}

          {projects?.map((project) => (
            <div
              key={project.id}
              className="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow"
            >
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                    {project.name}
                  </h3>
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    project.enabled
                      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                      : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
                  }`}>
                    {project.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                  <div><span className="font-medium">ID:</span> {project.id}</div>
                  <div><span className="font-medium">Type:</span> {project.type}</div>
                  <div><span className="font-medium">Platform:</span> {project.git_platform}</div>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleToggle(project.id, project.enabled)}
                  disabled={toggleProject.isPending}
                  className={`p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 ${
                    project.enabled ? 'text-green-600' : 'text-gray-400'
                  }`}
                  title={project.enabled ? 'Disable' : 'Enable'}
                >
                  <Power size={18} />
                </button>
                <button
                  onClick={() => {
                    console.log('Edit button clicked for project:', project);
                    setEditingProject(project);
                    console.log('editingProject set to:', project);
                  }}
                  className="p-2 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900 rounded"
                  title="Edit"
                >
                  <Edit2 size={18} />
                </button>
                <button
                  onClick={() => handleDelete(project.id)}
                  disabled={deleteProject.isPending}
                  className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900 rounded"
                  title="Delete"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 pt-4 space-y-2 text-sm">
              <div>
                <span className="text-gray-600 dark:text-gray-400">Repository:</span>
                <div className="text-gray-900 dark:text-white font-mono text-xs mt-1 break-all">
                  {project.repository}
                </div>
              </div>
              <div>
                <span className="text-gray-600 dark:text-gray-400">Path:</span>
                <div className="text-gray-900 dark:text-white font-mono text-xs mt-1 break-all">
                  {project.path}
                </div>
              </div>

              {project.test_command && (
                <div>
                  <span className="text-gray-600 dark:text-gray-400">Test Command:</span>
                  <div className="text-gray-900 dark:text-white font-mono text-xs mt-1">
                    {project.test_command}
                  </div>
                </div>
              )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>

    {/* Add/Edit Form Modal - Rendered outside main container */}
    {console.log('Modal check:', { showAddForm, editingProject, shouldShow: (showAddForm || editingProject) })}
    {(showAddForm || editingProject) && (
      <ProjectForm
        project={editingProject}
        onClose={() => {
          setShowAddForm(false);
          setEditingProject(null);
        }}
        onSave={async (data) => {
          try {
            if (editingProject) {
              await updateProject.mutateAsync({ id: editingProject.id, data });
            } else {
              await createProject.mutateAsync(data);
            }
            setShowAddForm(false);
            setEditingProject(null);
          } catch (err) {
            console.error('Save failed:', err);
          }
        }}
      />
    )}
    </>
  );
}
