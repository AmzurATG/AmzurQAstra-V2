import React from 'react'
import { Card } from '@common/components/ui/Card'
import { useProjectStore } from '@common/store/projectStore'
import { Cog6ToothIcon } from '@heroicons/react/24/outline'
import { Button } from '@common/components/ui/Button'
import { useNavigate } from 'react-router-dom'

interface CredentialsOverrideProps {
  projectId: string | undefined
  showCreds: boolean
  setShowCreds: (show: boolean) => void
  overrideUser: string
  setOverrideUser: (val: string) => void
  overridePass: string
  setOverridePass: (val: string) => void
  onSaveToProject?: () => Promise<void>
}

export const CredentialsOverride: React.FC<CredentialsOverrideProps> = ({
  projectId,
  showCreds,
  setShowCreds,
  overrideUser,
  setOverrideUser,
  overridePass,
  setOverridePass,
  onSaveToProject
}) => {
  const { currentProject } = useProjectStore()
  const navigate = useNavigate()
  const [isSaving, setIsSaving] = React.useState(false)
  const hasAppUrl = !!(currentProject?.app_url)

  const handleSave = async () => {
    if (!onSaveToProject) return
    setIsSaving(true)
    try {
      await onSaveToProject()
    } finally {
      setIsSaving(false)
    }
  }

  if (!hasAppUrl) {
    return (
      <Card className="border-amber-200 bg-amber-50">
        <div className="flex items-center justify-between">
          <p className="text-sm text-amber-800">
            Set your Application URL and login credentials in Project Settings before running tests.
          </p>
          <Button size="sm" onClick={() => navigate(`/projects/${projectId}/settings`)}>
            <Cog6ToothIcon className="w-4 h-4 mr-1" /> Go to Settings
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card className="bg-gray-50 border-gray-200">
      <div className="flex items-center justify-between">
        <div className="text-sm">
          <span className="text-gray-500">Target: </span>
          <span className="font-medium text-gray-900">{currentProject?.app_url}</span>
          {currentProject?.has_credentials ? (
            <span className="ml-3 text-gray-500">
              · Credentials: <span className="text-green-600 font-medium">{currentProject.app_username || 'configured'}</span>
            </span>
          ) : (
            <span className="ml-3 text-amber-600 text-xs">No credentials saved</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowCreds(!showCreds)} className="text-xs text-primary-600 hover:underline">
            {showCreds ? 'Hide' : overrideUser ? 'Credentials set ✓' : 'Set credentials for this run'}
          </button>
          <Button variant="ghost" size="sm" onClick={() => navigate(`/projects/${projectId}/settings`)}>
            <Cog6ToothIcon className="w-4 h-4 mr-1" /> Settings
          </Button>
        </div>
      </div>
      {showCreds && (
        <div className="mt-3 pt-3 border-t border-gray-200 grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Username / Email (override)</label>
            <input 
              value={overrideUser} 
              onChange={e => setOverrideUser(e.target.value)} 
              className="w-full p-2 border rounded-lg text-sm focus:ring-1 focus:ring-primary-500 outline-none" 
              placeholder={currentProject?.app_username || 'user@example.com'} 
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Password (override)</label>
            <input 
              type="password" 
              value={overridePass} 
              onChange={e => setOverridePass(e.target.value)} 
              className="w-full p-2 border rounded-lg text-sm focus:ring-1 focus:ring-primary-500 outline-none" 
              placeholder={currentProject?.has_credentials ? '••••••••  (saved in settings)' : 'Enter password'} 
            />
          </div>
          <p className="col-span-2 text-[10px] text-gray-500">
            {currentProject?.has_credentials
              ? 'Leave empty to use credentials from Project Settings. Fill to override for this run only.'
              : 'Enter credentials here or save them permanently in Project Settings.'}
          </p>
          <div className="col-span-2 flex justify-end gap-2 mt-1">
            <Button 
              size="xs" 
              variant="outline" 
              onClick={handleSave}
              disabled={!overrideUser || !overridePass || isSaving}
              isLoading={isSaving}
            >
              Save to Project Settings
            </Button>
          </div>
        </div>
      )}
    </Card>
  )
}
