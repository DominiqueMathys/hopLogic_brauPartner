import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { ApiError, fetchActivities } from '../../api/crm.ts'
import { ActivityTimeline } from '../../components/crm/ActivityTimeline.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { Card } from '../../components/ui/Card.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { activityTypeOptions, type ActivityList } from '../../domain/crm.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

export function ActivityListPage() {
  usePageTitle('Aktivitäten')
  const [params, setParams] = useSearchParams()
  const queryKey = params.toString()
  const [data, setData] = useState<ActivityList | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)
  const q = params.get('q') ?? ''
  const activityType = params.get('typ') ?? ''
  const includeArchived = params.get('archiv') === 'ja'
  const page = Number(params.get('seite') ?? '1')

  useEffect(() => {
    let active = true
    const current = new URLSearchParams(queryKey)
    void fetchActivities({
      q: current.get('q') ?? '',
      activityType: current.get('typ') ?? '',
      includeArchived: current.get('archiv') === 'ja',
      page: Number(current.get('seite') ?? '1') || 1,
    })
      .then((result) => {
        if (active) {
          setData(result)
          setError(null)
          setPending(false)
        }
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(caught instanceof ApiError ? caught.message : 'Die Verbindung zur API ist fehlgeschlagen.')
          setPending(false)
        }
      })
    return () => {
      active = false
    }
  }, [queryKey, reloadKey])

  function assign(changes: Record<string, string | null>) {
    setPending(true)
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      if (value) {
        next.set(key, value)
      } else {
        next.delete(key)
      }
    }
    next.delete('seite')
    setParams(next)
  }

  const pages = Math.max(1, Math.ceil((data?.total ?? 0) / (data?.page_size ?? 20)))

  return (
    <div className="mx-auto grid max-w-4xl gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Aktivitäten</h1>
          <p className="mt-2 text-sm leading-6 text-muted">Chronik der Gespräche, Besuche und Notizen. Neueste Einträge stehen oben.</p>
        </div>
        <Link to="/aktivitaeten/neu" className={cx(buttonStyles.base, buttonStyles.primary)}>
          Aktivität erfassen
        </Link>
      </header>
      <Card className="grid gap-4 p-4 md:grid-cols-3">
        <SearchBox key={q} initial={q} onSearch={(value) => assign({ q: value.trim() })} />
        <Select label="Aktivitätstyp" value={activityType} options={[{ value: '', label: 'Alle' }, ...activityTypeOptions]} onChange={(value) => assign({ typ: value })} />
        <Select
          label="Archiv"
          value={includeArchived ? 'ja' : 'nein'}
          options={[
            { value: 'nein', label: 'Ohne archivierte Aktivitäten' },
            { value: 'ja', label: 'Mit archivierten Aktivitäten' },
          ]}
          onChange={(value) => assign({ archiv: value === 'ja' ? 'ja' : null })}
        />
      </Card>
      <Card className="p-4">
        {error ? (
          <ErrorState title="Aktivitäten nicht verfügbar" description={error} />
        ) : pending || !data ? (
          <LoadingState label="Aktivitäten werden geladen" />
        ) : (
          <div className="grid gap-4">
            <p className="text-sm text-muted">{data.total === 1 ? '1 Aktivität gefunden' : `${data.total} Aktivitäten gefunden`}</p>
            <ActivityTimeline items={data.items} onChanged={() => setReloadKey((value) => value + 1)} />
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-muted">Seite {Number.isInteger(page) && page > 0 ? page : 1} von {pages}</p>
              <div className="flex gap-2">
                <Button variant="secondary" disabled={page <= 1} onClick={() => setParams((current) => { const next = new URLSearchParams(current); next.set('seite', String(page - 1)); if (page - 1 <= 1) next.delete('seite'); return next })}>Zurück</Button>
                <Button variant="secondary" disabled={page >= pages} onClick={() => setParams((current) => { const next = new URLSearchParams(current); next.set('seite', String(page + 1)); return next })}>Weiter</Button>
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}

function SearchBox({ initial, onSearch }: { initial: string; onSearch: (value: string) => void }) {
  const [value, setValue] = useState(initial)
  return (
    <form className="md:col-span-3 flex flex-wrap items-end gap-2" onSubmit={(event) => { event.preventDefault(); onSearch(value) }}>
      <div className="min-w-[16rem] flex-1">
        <Input label="Suche in Titel und Beschreibung" value={value} onChange={(event) => setValue(event.target.value)} />
      </div>
      <Button type="submit">Suchen</Button>
    </form>
  )
}
