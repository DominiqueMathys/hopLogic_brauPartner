import { useId, type ReactNode, type TextareaHTMLAttributes } from 'react'
import { cx } from '../../lib/cx.ts'
import { fieldClassName } from './Input.tsx'

type TextareaProps = {
  label: string
  hint?: ReactNode
  error?: string
  id?: string
} & TextareaHTMLAttributes<HTMLTextAreaElement>

export function Textarea({ label, hint, error, id, className, ...props }: TextareaProps) {
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
      <textarea
        {...props}
        id={inputId}
        className={cx(fieldClassName, 'min-h-28', error ? 'border-critical' : undefined, className)}
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
