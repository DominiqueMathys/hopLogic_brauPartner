export function BoundaryNotice({ topic }: { topic: 'products' | 'orders' }) {
  const text =
    topic === 'products'
      ? 'Dieser Katalog ist eine lokale CRM-Abbildung. Eine Synchronisation ist nur mit dem konfigurierten Connector möglich. Das Mock-ERP enthält fiktive Testdaten und ist keine Anbindung an das ERP des Liechtensteiner Brauhauses. Gespeicherte Bestellpositionen behalten ihren Preis.'
      : 'Der CRM-Status ist eine interne Angabe. Eine Übertragung an das Mock-ERP ist ein Test, keine Lieferung und keine Rechnung. Es besteht keine Verbindung zum ERP des Liechtensteiner Brauhauses.'
  return <p className="border border-gold bg-gold-soft px-4 py-3 text-sm leading-6 text-ink">{text}</p>
}
