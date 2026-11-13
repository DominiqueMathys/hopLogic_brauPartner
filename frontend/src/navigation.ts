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
    summary: 'Stammdaten, Status und Betreuung der Vertriebspartner.',
    phase: 'available',
  },
  {
    id: 'contacts',
    label: 'Kontakte',
    path: '/kontakte',
    summary: 'Kontaktpersonen, Zuordnung und Betreuung.',
    phase: 'available',
  },
  {
    id: 'opportunities',
    label: 'Verkaufschancen',
    path: '/verkaufschancen',
    summary: 'Offene Pipeline, gewonnene und verlorene Deals.',
    phase: 'available',
  },
  {
    id: 'orders',
    label: 'Bestellungen',
    path: '/bestellungen',
    summary: 'Dokumentierte CRM-Bestellungen ohne ERP-Übertragung.',
    phase: 'available',
  },
  {
    id: 'products',
    label: 'Produkte',
    path: '/produkte',
    summary: 'Lokaler Produktkatalog mit Richtpreisen in CHF.',
    phase: 'available',
  },
  {
    id: 'activities',
    label: 'Aktivitäten',
    path: '/aktivitaeten',
    summary: 'Telefonate, Besuche, Meetings und Gesprächsnotizen.',
    phase: 'available',
  },
  {
    id: 'tasks',
    label: 'Aufgaben',
    path: '/aufgaben',
    summary: 'Fälligkeiten, Prioritäten und Folgeaufgaben.',
    phase: 'available',
  },
  {
    id: 'service',
    label: 'Kundenservice',
    path: '/kundenservice',
    summary: 'Serviceanfragen, Reklamationen und Tickets.',
    phase: 'available',
  },
  {
    id: 'segments',
    label: 'Segmente',
    path: '/segmente',
    summary: 'Partnergruppen aus aktuellen CRM-Daten.',
    phase: 'available',
  },
  {
    id: 'campaigns',
    label: 'Kampagnen',
    path: '/kampagnen',
    summary: 'Marketingkampagnen, Zielgruppen und Nachrichtenvorlagen.',
    phase: 'available',
  },
  {
    id: 'care',
    label: 'Partnerbetreuung',
    path: '/partnerbetreuung',
    summary: 'Kontaktpausen, Betreuungstermine und Betreuungsregeln.',
    phase: 'available',
  },
  {
    id: 'automations',
    label: 'Automatisierungen',
    path: '/automatisierungen',
    summary: 'Interne CRM-Regeln mit Ausführungsprotokoll.',
    phase: 'available',
  },
  {
    id: 'notices',
    label: 'Benachrichtigungen',
    path: '/benachrichtigungen',
    summary: 'Interne Hinweise für den gewählten Anzeigenamen.',
    phase: 'available',
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
