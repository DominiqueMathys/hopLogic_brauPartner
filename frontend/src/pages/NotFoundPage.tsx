import { Link } from 'react-router'
import { buttonStyles } from '../components/ui/button-styles.ts'
import { ErrorState } from '../components/ui/ErrorState.tsx'
import { cx } from '../lib/cx.ts'
import { usePageTitle } from '../usePageTitle.ts'

export function NotFoundPage() {
  usePageTitle('Seite nicht gefunden')

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-3xl font-semibold tracking-tight">Seite nicht gefunden</h1>
      <div className="mt-6">
        <ErrorState
          title="Dieser Pfad gehört nicht zur Anwendung"
          description="Die Adresse ist unbekannt. Wechseln Sie über die Navigation oder kehren Sie zum Dashboard zurück."
          action={
            <Link to="/" className={cx(buttonStyles.base, buttonStyles.primary)}>
              Zum Dashboard
            </Link>
          }
        />
      </div>
    </div>
  )
}
