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
  id?: string
  disabled?: boolean
}

export function Select({ label, value, onChange, options, hint, id, disabled }: SelectProps) {
  const generatedId = useId()
  const selectId = id ?? generatedId
  const hintId = hint ? `${selectId}-hint` : undefined

  return (
    <div className="grid gap-1.5">
      <label htmlFor={selectId} className="text-sm font-semibold text-ink">
        {label}
      </label>
      <select
        id={selectId}
        className={cx(fieldClassName, 'min-h-11')}
        value={value}
        disabled={disabled}
        aria-describedby={hintId}
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
    </div>
  )
}
