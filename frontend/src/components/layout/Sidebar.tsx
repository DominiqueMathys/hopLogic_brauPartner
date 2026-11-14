import { NavLink } from 'react-router'
import { useAuth } from '../../auth.tsx'
import { NavIcon } from '../icons.tsx'
import { navAllowed, navigation, type NavItem } from '../../navigation.ts'
import { cx } from '../../lib/cx.ts'

type SidebarProps = {
  open: boolean
  collapsed: boolean
  onNavigate: () => void
}

export function Sidebar({ open, collapsed, onNavigate }: SidebarProps) {
  const { can } = useAuth()
  const items = navigation.filter((item) => navAllowed(item, can))
  return (
    <aside
      id="app-sidebar"
      className={cx(
        'fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-anthracite text-cream transition-transform md:static md:translate-x-0',
        open ? 'translate-x-0' : '-translate-x-full',
        collapsed ? 'md:w-[4.75rem]' : 'md:w-64',
      )}
    >
      <div className={cx('flex items-center gap-3 px-4 py-5', collapsed && 'md:justify-center md:px-2')}>
        <div className="flex h-10 w-10 shrink-0 items-center justify-center border border-gold-bright text-sm font-semibold">
          HL
        </div>
        <div className={cx(collapsed && 'md:hidden')}>
          <p className="text-sm leading-tight font-semibold">HopLogic</p>
          <p className="text-xs tracking-[0.16em] text-gold-bright uppercase">BrauPartner</p>
        </div>
      </div>
      <nav aria-label="Hauptnavigation" className="flex-1 overflow-y-auto px-2 pb-4">
        <ul className="grid gap-1">
          {items.map((item) => (
            <li key={item.id}>
              <SidebarLink item={item} collapsed={collapsed} onNavigate={onNavigate} />
            </li>
          ))}
        </ul>
      </nav>
      <p className={cx('px-4 py-4 text-xs text-sidebar-muted', collapsed && 'md:hidden')}>Liechtensteiner Brauhaus</p>
    </aside>
  )
}

function SidebarLink({ item, collapsed, onNavigate }: { item: NavItem; collapsed: boolean; onNavigate: () => void }) {
  return (
    <NavLink
      to={item.path}
      end={item.path === '/'}
      title={item.label}
      onClick={onNavigate}
      className={({ isActive }) =>
        cx(
          'flex min-h-11 items-center gap-3 border-l-2 px-3 text-sm focus-visible:outline-gold-bright',
          collapsed && 'md:justify-center md:px-0',
          isActive
            ? 'border-gold-bright bg-anthracite-raised font-semibold text-cream'
            : 'border-transparent text-sidebar-muted hover:bg-anthracite-hover hover:text-cream',
        )
      }
    >
      <NavIcon id={item.id} />
      <span className={cx(collapsed && 'md:sr-only')}>{item.label}</span>
    </NavLink>
  )
}
