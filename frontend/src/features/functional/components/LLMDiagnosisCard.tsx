import { SparklesIcon, LightBulbIcon } from '@heroicons/react/24/outline'

interface Props {
  diagnosis: string
  stepNumber: number
  action: string
}

export function LLMDiagnosisCard({ diagnosis, stepNumber, action }: Props) {
  return (
    <div className="mt-2 ml-6 rounded-lg border border-amber-200 bg-amber-50 p-3">
      <div className="flex items-start gap-2">
        <SparklesIcon className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600" />
        <div className="min-w-0 flex-1">
          <p className="mb-1 text-xs font-semibold text-amber-800">
            AI Diagnosis — Step #{stepNumber} ({action})
          </p>
          <p className="whitespace-pre-wrap text-xs leading-relaxed text-amber-900">
            {diagnosis}
          </p>
        </div>
        <LightBulbIcon className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-400" />
      </div>
    </div>
  )
}
