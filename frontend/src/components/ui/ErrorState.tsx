import type { ReactNode } from 'react'

type ErrorStateProps = {
  title: string
  description: string
  action?: ReactNode
}

export function ErrorState({ title, description, action }: ErrorStateProps) {
  return (
    <div role="alert" className="border border-critical/30 bg-critical-soft px-4 py-4">
      <p className="font-semibold text-critical">{title}</p>
      <p className="mt-1 max-w-xl text-sm leading-6 text-ink">{description}</p>
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  )
}
