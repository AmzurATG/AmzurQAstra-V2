import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useProjectStore } from '@common/store/projectStore'
import { projectsApi } from '@common/api/projects'
import { Card } from '@common/components/ui/Card'
import { Button } from '@common/components/ui/Button'
import { Input } from '@common/components/ui/Input'
import { PageLoader } from '@common/components/ui/Loader'
import { PlusIcon, FolderIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

export default function Projects() {
  const { projects, isLoading, fetchProjects } = useProjectStore()
  const [showCreate, setShowCreate] = useState(false)
  const [newProject, setNewProject] = useState({ name: '', description: '', app_url: '' })
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    try {
      await projectsApi.create(newProject)
      toast.success('Project created!')
      setShowCreate(false)
      setNewProject({ name: '', description: '', app_url: '' })
      fetchProjects()
    } catch (error) {
      toast.error('Failed to create project')
    } finally {
      setCreating(false)
    }
  }

  if (isLoading) return <PageLoader />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
          <p className="text-gray-600">Manage your testing projects</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <PlusIcon className="w-4 h-4 mr-2" />
          New Project
        </Button>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <Card>
          <form onSubmit={handleCreate} className="space-y-4">
            <h3 className="text-lg font-semibold">Create New Project</h3>
            <Input
              label="Project Name"
              value={newProject.name}
              onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
              required
            />
            <Input
              label="Description"
              value={newProject.description}
              onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
            />
            <Input
              label="Application URL"
              value={newProject.app_url}
              onChange={(e) => setNewProject({ ...newProject, app_url: e.target.value })}
              placeholder="https://app.example.com"
            />
            <div className="flex gap-2">
              <Button type="submit" isLoading={creating}>Create</Button>
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            </div>
          </form>
        </Card>
      )}

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map((project) => (
          <Link key={project.id} to={`/projects/${project.id}`}>
            <Card className="hover:shadow-md transition-shadow h-full">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-primary-100 rounded-lg">
                  <FolderIcon className="w-6 h-6 text-primary-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 truncate">{project.name}</h3>
                  <p className="text-sm text-gray-500 line-clamp-2">
                    {project.description || 'No description'}
                  </p>
                  {project.app_url && (
                    <p className="text-xs text-primary-600 mt-2 truncate">{project.app_url}</p>
                  )}
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>

      {projects.length === 0 && (
        <Card className="text-center py-12">
          <FolderIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">No projects yet</h3>
          <p className="text-gray-500 mt-1">Create your first project to get started</p>
          <Button onClick={() => setShowCreate(true)} className="mt-4">
            <PlusIcon className="w-4 h-4 mr-2" />
            Create Project
          </Button>
        </Card>
      )}
    </div>
  )
}
