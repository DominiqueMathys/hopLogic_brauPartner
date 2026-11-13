import type { ReactNode } from 'react'
import { cx } from '../../lib/cx.ts'

const tones = {
  neutral: 'bg-cream-deep text-ink',
  success: 'bg-success-soft text-success',
  warning: 'bg-warning-soft text-warning',
  critical: 'bg-critical-soft text-critical',
  accent: 'bg-gold-soft text-gold',
  petrol: 'bg-petrol-soft text-petrol',
} as const

type BadgeProps = {
  tone?: keyof typeof tones
  children: ReactNode
}

export function Badge({ tone = 'neutral', children }: BadgeProps) {
  return (
    <span className={cx('inline-flex items-center px-2 py-0.5 text-xs font-semibold tracking-wide', tones[tone])}>
      {children}
    </span>
  )
}
