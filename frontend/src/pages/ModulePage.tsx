import { Link } from 'react-router'
import { Badge } from '../components/ui/Badge.tsx'
import { buttonStyles } from '../components/ui/button-styles.ts'
import { Card } from '../components/ui/Card.tsx'
import { EmptyState } from '../components/ui/EmptyState.tsx'
import { cx } from '../lib/cx.ts'
import type { NavItem } from '../navigation.ts'
import { usePageTitle } from '../usePageTitle.ts'

type ModulePageProps = {
  item: NavItem
}

export function ModulePage({ item }: ModulePageProps) {
  usePageTitle(item.label)

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-3xl font-semibold tracking-tight">{item.label}</h1>
        <Badge tone="warning">In Entwicklung</Badge>
      </div>
      <p className="mt-3 text-base leading-7 text-muted">{item.summary}</p>
      <Card className="mt-6">
        <EmptyState
          title="Modul in Entwicklung"
          description="Die Erfassung und Verwaltung folgt in einer späteren Phase. Diese Seite ist erreichbar, enthält aber noch keine Fachdaten."
          action={
            <Link to="/" className={cx(buttonStyles.base, buttonStyles.secondary)}>
              Zurück zum Dashboard
            </Link>
          }
        />
      </Card>
    </div>
  )
}
