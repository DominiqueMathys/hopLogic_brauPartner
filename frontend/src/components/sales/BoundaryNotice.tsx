export function BoundaryNotice({ topic }: { topic: 'products' | 'orders' }) {
  const text =
    topic === 'products'
      ? 'Dieser Katalog ist eine lokale CRM-Abbildung. Artikel und Preise sind keine offiziellen Angaben des Liechtensteiner Brauhauses und werden nicht mit dem ERP synchronisiert.'
      : 'Bestellungen werden im CRM dokumentiert. Es erfolgt keine Übertragung ins ERP, keine Lagerprüfung und keine Rechnung. Versand- und Lieferstatus sind interne CRM-Angaben.'
  return <p className="border border-gold bg-gold-soft px-4 py-3 text-sm leading-6 text-ink">{text}</p>
}
