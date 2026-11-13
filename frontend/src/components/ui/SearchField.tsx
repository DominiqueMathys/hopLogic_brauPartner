import type { KeyboardEvent } from 'react'
import { Link } from 'react-router'
import { Input } from './Input.tsx'

export type SearchResult = {
  id: string
  label: string
  path: string
}

type SearchFieldProps = {
  label: string
  hint: string
  placeholder: string
  value: string
  onChange: (value: string) => void
  results: SearchResult[]
  onSelect: (path: string) => void
}

export function SearchField({
  label,
  hint,
  placeholder,
  value,
  onChange,
  results,
  onSelect,
}: SearchFieldProps) {
  const query = value.trim()
  const visible = query.length > 0

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter' && results[0]) {
      event.preventDefault()
      onSelect(results[0].path)
    }
  }

  return (
    <div>
      <Input
        label={label}
        hint={hint}
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
        autoComplete="off"
        role="searchbox"
      />
      {visible ? (
        <div className="mt-2 border border-line bg-card">
          {results.length === 0 ? (
            <p className="px-3 py-3 text-sm text-muted">Kein Menüpunkt passt zur Suche.</p>
          ) : (
            <ul aria-label="Suchergebnisse in der Navigation">
              {results.map((result) => (
                <li key={result.id}>
                  <Link
                    to={result.path}
                    className="block px-3 py-2 text-sm hover:bg-cream"
                    onClick={() => onSelect(result.path)}
                  >
                    {result.label}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  )
}
