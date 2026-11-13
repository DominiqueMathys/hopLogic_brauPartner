import type { NavIconId } from './components/icons.tsx'

export type NavPhase = 'available' | 'planned'

export type NavItem = {
  id: NavIconId
  label: string
  path: string
  summary: string
  phase: NavPhase
}

export const navigation: NavItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    path: '/',
    summary: 'Zentrale Arbeitsfläche für Vertrieb, Partnerbetreuung und Kundenservice',
    phase: 'available',
  },
  {
    id: 'partners',
    label: 'Vertriebspartner',
    path: '/vertriebspartner',
    summary: 'Stammdaten und Betreuung der Vertriebspartner.',
    phase: 'planned',
  },
  {
    id: 'contacts',
    label: 'Kontakte',
    path: '/kontakte',
    summary: 'Ansprechpersonen bei Partnern und Kunden.',
    phase: 'planned',
  },
  {
    id: 'opportunities',
    label: 'Verkaufschancen',
    path: '/verkaufschancen',
    summary: 'Offene und abgeschlossene Verkaufschancen.',
    phase: 'planned',
  },
  {
    id: 'orders',
    label: 'Bestellungen',
    path: '/bestellungen',
    summary: 'Aufträge und Bestellstatus.',
    phase: 'planned',
  },
  {
    id: 'activities',
    label: 'Aktivitäten',
    path: '/aktivitaeten',
    summary: 'Gespräche, Notizen und Termine.',
    phase: 'planned',
  },
  {
    id: 'tasks',
    label: 'Aufgaben',
    path: '/aufgaben',
    summary: 'Persönliche und gemeinsame Aufgaben.',
    phase: 'planned',
  },
  {
    id: 'service',
    label: 'Kundenservice',
    path: '/kundenservice',
    summary: 'Serviceanfragen und Tickets.',
    phase: 'planned',
  },
  {
    id: 'materials',
    label: 'Festmaterial',
    path: '/festmaterial',
    summary: 'Material für Feste und Einsätze.',
    phase: 'planned',
  },
  {
    id: 'reporting',
    label: 'Reporting',
    path: '/reporting',
    summary: 'Auswertungen für Vertrieb und Service.',
    phase: 'planned',
  },
  {
    id: 'settings',
    label: 'Einstellungen',
    path: '/einstellungen',
    summary: 'Systemstatus der technischen Grundlage. Weitere Einstellungen folgen.',
    phase: 'available',
  },
]

export function currentNavItem(pathname: string): NavItem | undefined {
  return navigation.find((item) => isNavActive(pathname, item.path))
}

export function isNavActive(pathname: string, path: string): boolean {
  if (path === '/') {
    return pathname === '/'
  }
  return pathname === path || pathname.startsWith(`${path}/`)
}
