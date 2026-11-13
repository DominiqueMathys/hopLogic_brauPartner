import { useId, type InputHTMLAttributes, type ReactNode } from 'react'
import { cx } from '../../lib/cx.ts'

export const fieldClassName =
  'w-full border border-line bg-card px-3 py-2 text-sm text-ink placeholder:text-muted'

type InputProps = {
  label: string
  hint?: ReactNode
  id?: string
} & InputHTMLAttributes<HTMLInputElement>

export function Input({ label, hint, id, className, ...props }: InputProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const hintId = hint ? `${inputId}-hint` : undefined

  return (
    <div className="grid gap-1.5">
      <label htmlFor={inputId} className="text-sm font-semibold text-ink">
        {label}
      </label>
      <input
        id={inputId}
        className={cx(fieldClassName, className)}
        aria-describedby={hintId}
        {...props}
      />
      {hint ? (
        <p id={hintId} className="text-xs leading-5 text-muted">
          {hint}
        </p>
      ) : null}
    </div>
  )
}
