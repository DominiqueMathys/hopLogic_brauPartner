import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, fetchPipeline, moveDeal } from '../../api/sales.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { addMoney, dealStageOptions, formatChf, openDealStageOptions, type PipelineBoard, type PipelineCard } from '../../domain/sales.ts'
import { choiceLabel, formatDate } from '../../domain/partners.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

function relocate(board: PipelineBoard, dealId: string, stage: string): PipelineBoard {
  let moved: PipelineCard | undefined
  const cleared = board.columns.map((column) => {
    const found = column.deals.find((deal) => deal.id === dealId)
    if (found) moved = found
    const deals = column.deals.filter((deal) => deal.id !== dealId)
    return { ...column, deals, count: deals.length, total_value: addMoney(deals.map((deal) => deal.estimated_value)) }
  })
  if (!moved) return board
  return {
    columns: cleared.map((column) => {
      if (column.stage !== stage) return column
      const deals = [...column.deals, moved as PipelineCard]
      return { ...column, deals, count: deals.length, total_value: addMoney(deals.map((deal) => deal.estimated_value)) }
    }),
  }
}

export function PipelinePage() {
  usePageTitle('Sales-Pipeline')
  const [owner, setOwner] = useState('')
  const [company, setCompany] = useState('')
  const [closeFrom, setCloseFrom] = useState('')
  const [closeTo, setCloseTo] = useState('')
  const [applied, setApplied] = useState({ owner: '', company: '', closeFrom: '', closeTo: '' })
  const [board, setBoard] = useState<PipelineBoard | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(true)
  const [dragging, setDragging] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void fetchPipeline({
      accountOwner: applied.owner,
      q: applied.company,
      closeFrom: applied.closeFrom,
      closeTo: applied.closeTo,
    })
      .then((result) => {
        if (active) {
          setBoard(result)
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
  }, [applied])

  async function dropOn(stage: string) {
    if (!board || !dragging) return
    const source = board.columns.find((column) => column.deals.some((deal) => deal.id === dragging))
    if (!source || source.stage === stage) {
      setDragging(null)
      return
    }
    const previous = board
    const dealId = dragging
    setDragging(null)
    setBoard(relocate(board, dealId, stage))
    try {
      await moveDeal(dealId, stage)
    } catch (caught: unknown) {
      setBoard(previous)
      setError(caught instanceof ApiError ? caught.message : 'Die Phase konnte nicht gespeichert werden. Die Karte steht wieder in der vorherigen Spalte.')
    }
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Sales-Pipeline</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            Eine Spalte pro offener Verkaufsphase. Gewonnen und Verloren erscheinen hier nicht. Das Verschieben wird in der Datenbank gespeichert.
          </p>
        </div>
        <Link to="/verkaufschancen" className={cx(buttonStyles.base, buttonStyles.secondary)}>
          Zur Liste
        </Link>
      </header>
      <form
        className="grid gap-3 md:grid-cols-4"
        onSubmit={(event) => {
          event.preventDefault()
          setPending(true)
          setApplied({ owner, company, closeFrom, closeTo })
        }}
      >
        <Input label="Betreuung" value={owner} onChange={(event) => setOwner(event.target.value)} />
        <Input label="Unternehmen oder Titel" value={company} onChange={(event) => setCompany(event.target.value)} />
        <Input label="Abschluss von" type="date" value={closeFrom} onChange={(event) => setCloseFrom(event.target.value)} />
        <Input label="Abschluss bis" type="date" value={closeTo} onChange={(event) => setCloseTo(event.target.value)} />
        <button type="submit" className={cx(buttonStyles.base, buttonStyles.primary, 'md:col-span-4 md:justify-self-start')}>
          Filter anwenden
        </button>
      </form>
      {error ? <ErrorState title="Pipeline" description={error} /> : null}
      {pending && !board ? <LoadingState label="Pipeline wird geladen" /> : null}
      {board ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          {board.columns.map((column) => (
            <section
              key={column.stage}
              aria-label={choiceLabel(dealStageOptions, column.stage)}
              className="grid content-start gap-2 border border-line bg-cream p-2"
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault()
                void dropOn(column.stage)
              }}
            >
              <header>
                <h2 className="text-sm font-semibold">{choiceLabel(openDealStageOptions, column.stage)}</h2>
                <p className="text-xs text-muted">
                  {column.count} · {formatChf(column.total_value)}
                </p>
              </header>
              {column.deals.length === 0 ? <p className="px-1 py-4 text-sm text-muted">Keine Deals</p> : null}
              {column.deals.map((deal) => (
                <article
                  key={deal.id}
                  draggable
                  onDragStart={() => setDragging(deal.id)}
                  className="cursor-grab border border-line bg-card p-3"
                >
                  <p className="text-xs text-muted">{deal.company_name}</p>
                  <Link to={`/verkaufschancen/${deal.id}`} className="mt-1 block font-semibold text-petrol">
                    {deal.title}
                  </Link>
                  <p className="mt-2 text-sm">{formatChf(deal.estimated_value)}</p>
                  <p className="text-xs text-muted">{deal.account_owner ?? 'Keine Betreuung'}</p>
                  <p className="text-xs text-muted">{formatDate(deal.expected_close_on)}</p>
                  {deal.is_demo ? <Badge tone="accent">Testdaten</Badge> : null}
                  {deal.is_overdue ? <Badge tone="warning">Überfällig</Badge> : null}
                </article>
              ))}
            </section>
          ))}
        </div>
      ) : null}
    </div>
  )
}
