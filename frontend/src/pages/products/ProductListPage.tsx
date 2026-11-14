import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { ApiError, deactivateProduct, fetchProducts } from '../../api/sales.ts'
import { BoundaryNotice } from '../../components/sales/BoundaryNotice.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog.tsx'
import { DataTable, type DataColumn } from '../../components/ui/DataTable.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { containerOptions, formatChf, productCategoryOptions, type Product, type ProductList } from '../../domain/sales.ts'
import { choiceLabel, formatDateTime } from '../../domain/partners.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

export function ProductListPage() {
  usePageTitle('Produkte')
  const [params, setParams] = useSearchParams()
  const queryKey = params.toString()
  const [data, setData] = useState<ProductList | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(true)
  const [target, setTarget] = useState<Product | null>(null)

  useEffect(() => {
    let active = true
    const current = new URLSearchParams(queryKey)
    void fetchProducts({
      q: current.get('q') ?? '',
      category: current.get('kategorie') ?? '',
      includeInactive: current.get('inaktiv') === '1',
    })
      .then((list) => {
        if (active) {
          setData(list)
          setError(null)
          setPending(false)
        }
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(caught instanceof ApiError ? caught.message : 'Die Produkte konnten nicht geladen werden.')
          setPending(false)
        }
      })
    return () => {
      active = false
    }
  }, [queryKey])

  function assign(changes: Record<string, string | null>) {
    setPending(true)
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value)
      else next.delete(key)
    }
    setParams(next)
  }

  const columns: DataColumn<Product>[] = [
    {
      id: 'name',
      header: 'Produkt',
      cell: (row) => (
        <Link to={`/produkte/${row.id}/bearbeiten`} className="font-semibold text-petrol">
          {row.name}
        </Link>
      ),
    },
    { id: 'sku', header: 'Artikelnummer', cell: (row) => row.sku },
    { id: 'erp', header: 'ERP-Quelle', cell: (row) => row.erp_source === 'mock' ? 'Mock-ERP, Testdaten' : 'CRM' },
    { id: 'synced', header: 'Letzte Synchronisation', cell: (row) => row.erp_synced_at ? formatDateTime(row.erp_synced_at) : 'Keine' },
    { id: 'category', header: 'Kategorie', cell: (row) => choiceLabel(productCategoryOptions, row.category) },
    { id: 'container', header: 'Gebinde', cell: (row) => `${choiceLabel(containerOptions, row.container_type)} ${row.container_size ?? ''}`.trim() },
    { id: 'price', header: 'Richtpreis', cell: (row) => formatChf(row.list_price) },
    { id: 'vat', header: 'MWST', cell: (row) => `${row.vat_rate} %` },
    {
      id: 'state',
      header: 'Status',
      cell: (row) => (
        <span className="flex flex-wrap items-center gap-2">
          {row.is_demo ? <Badge tone="accent">Demo</Badge> : null}
          {row.is_active ? <Badge tone="success">Aktiv</Badge> : <Badge tone="neutral">Inaktiv</Badge>}
          {row.is_active ? (
            <Button variant="ghost" onClick={() => setTarget(row)}>
              Deaktivieren
            </Button>
          ) : null}
        </span>
      ),
    },
  ]

  return (
    <div className="mx-auto grid max-w-6xl gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Produkte</h1>
          <p className="mt-2 text-sm leading-6 text-muted">Lokaler Produktkatalog für CRM-Bestellungen. Preise sind Dezimalwerte in CHF.</p>
        </div>
        <Link to="/produkte/neu" className={cx(buttonStyles.base, buttonStyles.primary)}>
          Neues Produkt
        </Link>
      </header>
      <BoundaryNotice topic="products" />
      <div className="grid gap-3 md:grid-cols-3">
        <Input label="Suche" value={params.get('q') ?? ''} onChange={(event) => assign({ q: event.target.value || null })} />
        <Select
          label="Kategorie"
          value={params.get('kategorie') ?? ''}
          onChange={(value) => assign({ kategorie: value || null })}
          options={[{ value: '', label: 'Alle Kategorien' }, ...productCategoryOptions]}
        />
        <Select
          label="Status"
          value={params.get('inaktiv') === '1' ? 'alle' : 'aktiv'}
          onChange={(value) => assign({ inaktiv: value === 'alle' ? '1' : null })}
          options={[
            { value: 'aktiv', label: 'Nur aktive' },
            { value: 'alle', label: 'Inklusive inaktive' },
          ]}
        />
      </div>
      {error ? <ErrorState title="Produkte nicht geladen" description={error} /> : null}
      {pending && !data ? <LoadingState label="Produkte werden geladen" /> : null}
      {data ? (
        <DataTable
          caption="Produktkatalog"
          columns={columns}
          rows={data.items}
          rowKey={(row) => row.id}
          empty={<EmptyState title="Keine Produkte" description="Der Katalog enthält für diesen Filter keine Artikel." />}
        />
      ) : null}
      <ConfirmDialog
        open={target !== null}
        title="Produkt deaktivieren"
        description="Inaktive Produkte können nicht mehr in neue Bestellungen aufgenommen werden. Bestehende Bestellungen behalten den gespeicherten Stand."
        confirmLabel="Deaktivieren"
        tone="danger"
        onCancel={() => setTarget(null)}
        onConfirm={() => {
          if (!target) return
          void deactivateProduct(target.id)
            .then((saved) => {
              setData((current) =>
                current
                  ? {
                      ...current,
                      items: current.items.map((item) => (item.id === saved.id ? saved : item)),
                    }
                  : current,
              )
              setTarget(null)
            })
            .catch((caught: unknown) => {
              setTarget(null)
              setError(caught instanceof ApiError ? caught.message : 'Das Produkt konnte nicht deaktiviert werden.')
            })
        }}
      />
    </div>
  )
}
