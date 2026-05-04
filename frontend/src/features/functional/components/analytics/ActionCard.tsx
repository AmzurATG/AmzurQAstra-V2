import type { ReactNode } from 'react'

import { Card } from '@common/components/ui/Card'

type Props = {
  title: string
  hint?: string
  children: ReactNode
}

export function ActionCard({ title, hint, children }: Props) {
  return (
    <Card className="p-4 h-full">
      <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
      {hint ? <p className="text-xs text-gray-500 mt-1 mb-3">{hint}</p> : <div className="mb-3" />}
      {children}
    </Card>
  )
}
