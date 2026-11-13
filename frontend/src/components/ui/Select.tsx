import { useId } from 'react'
import { fieldClassName } from './Input.tsx'
import { cx } from '../../lib/cx.ts'

export type SelectOption = {
  value: string
  label: string
}

type SelectProps = {
  label: string
  value: string
  onChange: (value: string) => void
  options: SelectOption[]
  hint?: string
  error?: string
  id?: string
  disabled?: boolean
}

export function Select({ label, value, onChange, options, hint, error, id, disabled }: SelectProps) {
  const generatedId = useId()
  const selectId = id ?? generatedId
  const hintId = hint ? `${selectId}-hint` : undefined
  const errorId = error ? `${selectId}-error` : undefined
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined

  return (
    <div className="grid gap-1.5">
      <label htmlFor={selectId} className="text-sm font-semibold text-ink">
        {label}
      </label>
      <select
        id={selectId}
        className={cx(fieldClassName, 'min-h-11', error ? 'border-critical' : undefined)}
        value={value}
        disabled={disabled}
        aria-describedby={describedBy}
        aria-invalid={error ? true : undefined}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
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
