import { cx } from '../../lib/cx.ts'

const tones = {
  success: 'bg-success',
  warning: 'bg-warning',
  critical: 'bg-critical',
  pending: 'bg-gold',
} as const

type StatusIndicatorProps = {
  tone: keyof typeof tones
  label: string
}

export function StatusIndicator({ tone, label }: StatusIndicatorProps) {
  return (
    <span className="inline-flex items-center gap-2 text-sm font-semibold text-ink">
      <span className={cx('h-2.5 w-2.5', tones[tone])} aria-hidden="true" />
      <span role="status">{label}</span>
    </span>
  )
}
