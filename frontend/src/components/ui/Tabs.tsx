import { useId, useState, type ReactNode } from 'react'
import { cx } from '../../lib/cx.ts'

export type TabItem = {
  id: string
  label: string
  content: ReactNode
}

type TabsProps = {
  tabs: TabItem[]
  label: string
  initialId?: string
}

export function Tabs({ tabs, label, initialId }: TabsProps) {
  const baseId = useId()
  const [active, setActive] = useState(initialId ?? tabs[0]?.id ?? '')

  function move(offset: number) {
    const index = tabs.findIndex((tab) => tab.id === active)
    const next = tabs[(index + offset + tabs.length) % tabs.length]
    if (next) {
      setActive(next.id)
    }
  }

  return (
    <div>
      <div role="tablist" aria-label={label} className="flex gap-1 border-b border-line" onKeyDown={(event) => {
        if (event.key === 'ArrowRight') {
          event.preventDefault()
          move(1)
        }
        if (event.key === 'ArrowLeft') {
          event.preventDefault()
          move(-1)
        }
      }}>
        {tabs.map((tab) => {
          const selected = tab.id === active
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              id={`${baseId}-${tab.id}-tab`}
              aria-selected={selected}
              aria-controls={`${baseId}-${tab.id}-panel`}
              tabIndex={selected ? 0 : -1}
              className={cx(
                'min-h-11 px-4 text-sm font-semibold',
                selected ? 'border-b-2 border-petrol text-petrol' : 'text-muted hover:text-ink',
              )}
              onClick={() => setActive(tab.id)}
            >
              {tab.label}
            </button>
          )
        })}
      </div>
      {tabs.map((tab) => (
        <div
          key={tab.id}
          role="tabpanel"
          id={`${baseId}-${tab.id}-panel`}
          aria-labelledby={`${baseId}-${tab.id}-tab`}
          hidden={tab.id !== active}
          className="pt-5"
        >
          {tab.content}
        </div>
      ))}
    </div>
  )
}
