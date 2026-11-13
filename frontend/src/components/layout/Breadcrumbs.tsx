import { Link, useLocation } from 'react-router'
import { currentNavItem } from '../../navigation.ts'

function partnerTrail(pathname: string): string[] {
  if (pathname === '/vertriebspartner/neu') {
    return ['Neuer Partner']
  }
  if (/^\/vertriebspartner\/[^/]+\/bearbeiten$/.test(pathname)) {
    return ['Bearbeiten']
  }
  if (/^\/vertriebspartner\/[^/]+$/.test(pathname)) {
    return ['Partner']
  }
  return []
}

export function Breadcrumbs() {
  const { pathname } = useLocation()
  const current = currentNavItem(pathname)
  const onDashboard = pathname === '/'
  const trail = partnerTrail(pathname)

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
