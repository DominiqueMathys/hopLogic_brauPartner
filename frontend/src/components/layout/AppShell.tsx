import { useEffect, useState } from 'react'
import { Outlet } from 'react-router'
import { Sidebar } from './Sidebar.tsx'
import { Header } from './Header.tsx'

export function AppShell() {
  const [open, setOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const [desktop, setDesktop] = useState(() => window.matchMedia('(min-width: 768px)').matches)

  useEffect(() => {
    const media = window.matchMedia('(min-width: 768px)')
    function update() {
      setDesktop(media.matches)
    }
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  const menuExpanded = desktop ? !collapsed : open
  const menuLabel = menuExpanded ? 'Navigation ausblenden' : 'Navigation einblenden'

  function toggleMenu() {
    if (window.matchMedia('(min-width: 768px)').matches) {
      setCollapsed((current) => !current)
      return
    }
    setOpen((current) => !current)
  }

  return (
    <div className="min-h-screen bg-cream text-ink">
      <a
        href="#inhalt"
        className="absolute top-3 left-3 z-50 -translate-y-20 bg-card px-3 py-2 text-sm font-semibold focus:translate-y-0"
      >
        Zum Inhalt
      </a>
      {open ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-anthracite/45 md:hidden"
          aria-label="Navigation schliessen"
          onClick={() => setOpen(false)}
        />
      ) : null}
      <div className="flex min-h-screen">
        <Sidebar open={open} collapsed={collapsed} onNavigate={() => setOpen(false)} />
        <div className="flex min-w-0 flex-1 flex-col">
          <Header menuExpanded={menuExpanded} menuLabel={menuLabel} onToggleMenu={toggleMenu} />
          <main id="inhalt" className="flex-1 px-4 py-6 md:px-8 md:py-8">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}
