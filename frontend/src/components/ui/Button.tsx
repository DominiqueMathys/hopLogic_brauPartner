import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { cx } from '../../lib/cx.ts'
import { buttonStyles } from './button-styles.ts'

type ButtonProps = {
  variant?: keyof Omit<typeof buttonStyles, 'base'>
  children: ReactNode
} & ButtonHTMLAttributes<HTMLButtonElement>

export function Button({ variant = 'primary', className, children, type = 'button', ...props }: ButtonProps) {
  return (
    <button type={type} className={cx(buttonStyles.base, buttonStyles[variant], className)} {...props}>
      {children}
    </button>
  )
}
