/**
 * Project form page for adding/editing projects
 */
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useProject, useCreateProject, useUpdateProject } from '../hooks/useProjects';
import { ProjectForm } from '../components/ProjectForm';

export function ProjectFormPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEditing = !!id;

  const { data: project, isLoading } = useProject(id || '');
  const createProject = useCreateProject();
  const updateProject = useUpdateProject();

  if (isEditing && isLoading) {
    return (
      <div className="p-8">
        <div className="text-gray-600 dark:text-gray-400">Loading project...</div>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-gray-50 dark:bg-gray-900">
      <div className="max-w-2xl mx-auto py-8 px-4">
        {/* Back button */}
        <button
          onClick={() => navigate('/projects')}
          className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-6 transition-colors"
        >
          <ArrowLeft size={20} />
          <span>Back to Projects</span>
        </button>

        {/* Page header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {isEditing ? 'Edit Project' : 'New Project'}
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            {isEditing ? 'Update project configuration' : 'Add a new project to Lazy_Bird'}
          </p>
        </div>

        {/* Form card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <ProjectForm
            project={project || null}
            onClose={() => navigate('/projects')}
            onSave={async (data) => {
              if (isEditing && id) {
                await updateProject.mutateAsync({ id, data });
              } else {
                await createProject.mutateAsync(data);
              }
            }}
          />
        </div>
      </div>
    </div>
  );
}
