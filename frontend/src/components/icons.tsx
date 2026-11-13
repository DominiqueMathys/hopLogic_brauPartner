import type { ReactNode } from 'react'

type IconProps = {
  className?: string
}

function IconFrame({ className, children }: IconProps & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className ?? 'h-5 w-5'}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  )
}

export function DashboardIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <rect x="3.5" y="3.5" width="7" height="7" />
      <rect x="13.5" y="3.5" width="7" height="7" />
      <rect x="3.5" y="13.5" width="7" height="7" />
      <rect x="13.5" y="13.5" width="7" height="7" />
    </IconFrame>
  )
}

export function PartnersIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <path d="M4 20.5V6.5h6v14" />
      <path d="M10 20.5V9.5h10v11" />
      <path d="M6.5 9.5v.01M6.5 13v.01M6.5 16.5v.01M13.5 13v.01M17 13v.01M13.5 16.5v.01M17 16.5v.01" />
    </IconFrame>
  )
}

export function ContactsIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <circle cx="9" cy="9" r="3" />
      <path d="M4.5 19.5c.6-2.6 2.4-4 4.5-4s3.9 1.4 4.5 4" />
      <circle cx="17" cy="10" r="2.2" />
      <path d="M16 15.6c1.8.2 3.2 1.3 3.8 3.4" />
    </IconFrame>
  )
}

export function OpportunitiesIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="12" cy="12" r="1" />
    </IconFrame>
  )
}

export function ProductsIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <path d="M8 3.5h8v4H8z" />
      <path d="M7 7.5h10l-1 13H8l-1-13z" />
    </IconFrame>
  )
}

export function OrdersIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <path d="M7 4.5h10l1.5 3H5.5L7 4.5z" />
      <path d="M5.5 7.5h13v12h-13z" />
      <path d="M9 12h6" />
    </IconFrame>
  )
}

export function ActivitiesIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <path d="M4 13h3l2-5 3 9 2-4h6" />
    </IconFrame>
  )
}

export function TasksIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <rect x="4.5" y="4.5" width="15" height="15" />
      <path d="M8 12.2l2.4 2.4L16.2 9" />
    </IconFrame>
  )
}

export function SegmentsIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <circle cx="8" cy="8" r="2.2" />
      <circle cx="16" cy="8" r="2.2" />
      <circle cx="12" cy="15.5" r="2.2" />
    </IconFrame>
  )
}

export function ServiceIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <path d="M5 13a7 7 0 0 1 14 0" />
      <rect x="3.5" y="13" width="4" height="6" />
      <rect x="16.5" y="13" width="4" height="6" />
      <path d="M12 19.5v1" />
    </IconFrame>
  )
}

export function MaterialsIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <path d="M3.5 8 12 4l8.5 4L12 12 3.5 8z" />
      <path d="M3.5 8v8L12 20l8.5-4V8" />
      <path d="M12 12v8" />
    </IconFrame>
  )
}

export function ReportingIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <path d="M4 19.5h16" />
      <path d="M7 16V10" />
      <path d="M12 16V6" />
      <path d="M17 16v-4" />
    </IconFrame>
  )
}

export function SettingsIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3.5v2.2M12 18.3v2.2M4.8 6.2l1.6 1.6M17.6 16.2l1.6 1.6M3.5 12h2.2M18.3 12h2.2M4.8 17.8l1.6-1.6M17.6 7.8l1.6-1.6" />
    </IconFrame>
  )
}

export function SearchIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <circle cx="11" cy="11" r="6" />
      <path d="M15.5 15.5 20 20" />
    </IconFrame>
  )
}

export function BellIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <path d="M6 16.5h12l-1.2-2V10a4.8 4.8 0 0 0-9.6 0v4.5L6 16.5z" />
      <path d="M10 16.5a2 2 0 0 0 4 0" />
    </IconFrame>
  )
}

export function UserIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <circle cx="12" cy="9" r="3" />
      <path d="M5.5 19c.8-2.8 2.8-4.2 6.5-4.2S17.7 16.2 18.5 19" />
    </IconFrame>
  )
}

export function MenuIcon(props: IconProps) {
  return (
    <IconFrame {...props}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </IconFrame>
  )
}

const navIcons = {
  dashboard: DashboardIcon,
  partners: PartnersIcon,
  contacts: ContactsIcon,
  opportunities: OpportunitiesIcon,
  orders: OrdersIcon,
  products: ProductsIcon,
  activities: ActivitiesIcon,
  tasks: TasksIcon,
  service: ServiceIcon,
  segments: SegmentsIcon,
  materials: MaterialsIcon,
  reporting: ReportingIcon,
  settings: SettingsIcon,
} as const

export type NavIconId = keyof typeof navIcons

export function NavIcon({ id, className }: { id: NavIconId; className?: string }) {
  const Icon = navIcons[id]
  return <Icon className={className} />
}
