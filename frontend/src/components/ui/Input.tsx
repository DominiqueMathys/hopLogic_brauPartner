import { useId, type InputHTMLAttributes, type ReactNode } from 'react'
import { cx } from '../../lib/cx.ts'

export const fieldClassName =
  'w-full border border-line bg-card px-3 py-2 text-sm text-ink placeholder:text-muted'

type InputProps = {
  label: string
  hint?: ReactNode
  error?: string
  id?: string
} & InputHTMLAttributes<HTMLInputElement>

export function Input({ label, hint, error, id, className, ...props }: InputProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const hintId = hint ? `${inputId}-hint` : undefined
  const errorId = error ? `${inputId}-error` : undefined
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined

  return (
    <div className="grid gap-1.5">
      <label htmlFor={inputId} className="text-sm font-semibold text-ink">
        {label}
      </label>
      <input
        {...props}
        id={inputId}
        className={cx(fieldClassName, error ? 'border-critical' : undefined, className)}
        aria-describedby={describedBy}
        aria-invalid={error ? true : undefined}
      />
      {hint ? (
        <p id={hintId} className="text-xs leading-5 text-muted">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="text-xs leading-5 text-critical">
          {error}
        </p>
      ) : null}
    </div>
  )
}
