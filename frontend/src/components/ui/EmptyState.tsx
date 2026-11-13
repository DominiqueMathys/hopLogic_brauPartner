import type { ReactNode } from 'react'
import { cx } from '../../lib/cx.ts'

type EmptyStateProps = {
  title: string
  description: string
  compact?: boolean
  action?: ReactNode
}

export function EmptyState({ title, description, compact = false, action }: EmptyStateProps) {
  return (
    <div className={cx('text-center', compact ? 'px-2 py-4' : 'px-4 py-8')}>
      <p className={cx('font-semibold text-ink', compact ? 'text-sm' : 'text-base')}>{title}</p>
      <p className={cx('mx-auto max-w-md text-muted', compact ? 'mt-1 text-sm leading-5' : 'mt-2 text-sm leading-6')}>
        {description}
      </p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  )
}
