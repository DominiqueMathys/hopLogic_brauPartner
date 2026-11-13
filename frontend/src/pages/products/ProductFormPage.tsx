import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { ApiError, createProduct, fetchProduct, updateProduct } from '../../api/sales.ts'
import { BoundaryNotice } from '../../components/sales/BoundaryNotice.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Textarea } from '../../components/ui/Textarea.tsx'
import { containerOptions, emptyProductInput, productCategoryOptions, productToForm, type ProductInput } from '../../domain/sales.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

export function ProductCreatePage() {
  return <ProductForm />
}

export function ProductEditPage() {
  const { productId = '' } = useParams()
  return <ProductForm productId={productId} />
}

function ProductForm({ productId }: { productId?: string }) {
  usePageTitle(productId ? 'Produkt bearbeiten' : 'Neues Produkt')
  const navigate = useNavigate()
  const [form, setForm] = useState<ProductInput>(emptyProductInput())
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [pending, setPending] = useState(Boolean(productId))
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!productId) return
    let active = true
    void fetchProduct(productId)
      .then((product) => {
        if (!active) return
        setForm(productToForm(product))
        setPending(false)
      })
      .catch((caught: unknown) => {
        if (!active) return
        setError(caught instanceof ApiError ? caught.message : 'Das Produkt konnte nicht geladen werden.')
        setPending(false)
      })
    return () => {
      active = false
    }
  }, [productId])

  function setField<K extends keyof ProductInput>(field: K, value: ProductInput[K]) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function save() {
    setSaving(true)
    setError(null)
    try {
      const saved = productId ? await updateProduct(productId, form) : await createProduct(form)
      void navigate(`/produkte/${saved.id}/bearbeiten`)
    } catch (caught: unknown) {
      if (caught instanceof ApiError) {
        setError(caught.message)
        setFieldErrors(caught.fieldErrors)
      } else {
        setError('Das Produkt konnte nicht gespeichert werden.')
      }
    } finally {
      setSaving(false)
    }
  }

  if (pending) return <LoadingState label="Produkt wird geladen" />

  return (
    <div className="mx-auto grid max-w-3xl gap-4">
      <h1 className="text-3xl font-semibold tracking-tight">{productId ? 'Produkt bearbeiten' : 'Neues Produkt'}</h1>
      <BoundaryNotice topic="products" />
      {error ? <ErrorState title="Speichern nicht möglich" description={error} /> : null}
      <div className="grid gap-3 sm:grid-cols-2">
        <Input label="Artikelnummer" value={form.sku} error={fieldErrors.sku} onChange={(event) => setField('sku', event.target.value)} />
        <Input label="Produktname" value={form.name} error={fieldErrors.name} onChange={(event) => setField('name', event.target.value)} />
        <Select label="Kategorie" value={form.category} onChange={(value) => setField('category', value)} options={productCategoryOptions} />
        <Select label="Gebindeart" value={form.container_type} onChange={(value) => setField('container_type', value)} options={containerOptions} />
        <Input label="Gebindegrösse" value={form.container_size} onChange={(event) => setField('container_size', event.target.value)} />
        <Input label="Verkaufseinheit" value={form.sales_unit} onChange={(event) => setField('sales_unit', event.target.value)} />
        <Input label="Richtpreis in CHF" value={form.list_price} error={fieldErrors.list_price} onChange={(event) => setField('list_price', event.target.value)} />
        <Input label="Mehrwertsteuersatz in Prozent" value={form.vat_rate} error={fieldErrors.vat_rate} onChange={(event) => setField('vat_rate', event.target.value)} />
      </div>
      <Textarea label="Beschreibung" value={form.description} onChange={(event) => setField('description', event.target.value)} />
      <Select
        label="Status"
        value={form.is_active ? 'aktiv' : 'inaktiv'}
        onChange={(value) => setField('is_active', value === 'aktiv')}
        options={[
          { value: 'aktiv', label: 'Aktiv' },
          { value: 'inaktiv', label: 'Inaktiv' },
        ]}
      />
      <div className="flex gap-2">
        <Button disabled={saving} onClick={() => void save()}>
          Speichern
        </Button>
        <Link to="/produkte" className={cx(buttonStyles.base, buttonStyles.secondary)}>
          Zurück
        </Link>
      </div>
    </div>
  )
}
