import type { ReactNode } from 'react'
import { cx } from '../../lib/cx.ts'

type CardProps = {
  children: ReactNode
  className?: string
}

export function Card({ children, className }: CardProps) {
  return (
    <div className={cx('border border-line bg-card shadow-[0_1px_2px_rgba(27,36,43,0.05)]', className)}>
      {children}
    </div>
  )
}
