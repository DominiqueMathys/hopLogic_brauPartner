import { Link, useLocation } from 'react-router'
import { currentNavItem } from '../../navigation.ts'

function detailTrail(pathname: string, root: string, labels: { create: string; edit: string; detail: string }): string[] {
  if (pathname === `${root}/neu`) {
    return [labels.create]
  }
  if (new RegExp(`^${root}/[^/]+/bearbeiten$`).test(pathname)) {
    return [labels.edit]
  }
  if (new RegExp(`^${root}/[^/]+$`).test(pathname)) {
    return [labels.detail]
  }
  return []
}

function pageTrail(pathname: string): string[] {
  return [
    ...detailTrail(pathname, '/vertriebspartner', { create: 'Neuer Partner', edit: 'Bearbeiten', detail: 'Partner' }),
    ...detailTrail(pathname, '/kontakte', { create: 'Neuer Kontakt', edit: 'Bearbeiten', detail: 'Kontakt' }),
    ...detailTrail(pathname, '/aktivitaeten', { create: 'Neue Aktivität', edit: 'Bearbeiten', detail: 'Aktivität' }),
    ...detailTrail(pathname, '/aufgaben', { create: 'Neue Aufgabe', edit: 'Bearbeiten', detail: 'Aufgabe' }),
  ]
}

export function Breadcrumbs() {
  const { pathname } = useLocation()
  const current = currentNavItem(pathname)
  const onDashboard = pathname === '/'
  const trail = pageTrail(pathname)

  return (
    <nav aria-label="Brotkrumen">
      <ol className="flex flex-wrap items-center gap-1 text-xs text-muted">
        <li>
          {onDashboard ? (
            <span aria-current="page">Dashboard</span>
          ) : (
            <Link to="/" className="hover:text-ink">
              Dashboard
            </Link>
          )}
        </li>
        {onDashboard ? null : (
          <li className="flex items-center gap-1" aria-current={trail.length === 0 ? 'page' : undefined}>
            <span aria-hidden="true">/</span>
            {current && trail.length > 0 ? (
              <Link to={current.path} className="hover:text-ink">
                {current.label}
              </Link>
            ) : (
              <span>{current?.label ?? 'Seite'}</span>
            )}
          </li>
        )}
        {trail.map((label) => (
          <li key={label} className="flex items-center gap-1" aria-current="page">
            <span aria-hidden="true">/</span>
            <span>{label}</span>
          </li>
        ))}
      </ol>
    </nav>
  )
}
