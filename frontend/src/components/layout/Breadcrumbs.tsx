import { Link, useLocation } from 'react-router'
import { currentNavItem } from '../../navigation.ts'

export function Breadcrumbs() {
  const { pathname } = useLocation()
  const current = currentNavItem(pathname)
  const onDashboard = pathname === '/'

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
          <li className="flex items-center gap-1" aria-current="page">
            <span aria-hidden="true">/</span>
            <span>{current?.label ?? 'Seite'}</span>
          </li>
        )}
      </ol>
    </nav>
  )
}
