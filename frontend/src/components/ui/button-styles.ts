export const buttonStyles = {
  base: 'inline-flex min-h-11 items-center justify-center gap-2 px-4 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60',
  primary: 'bg-petrol text-cream hover:bg-petrol-strong',
  secondary: 'border border-line bg-card text-ink hover:bg-cream-deep',
  ghost: 'text-ink hover:bg-cream-deep',
  danger: 'bg-critical text-white hover:bg-[#842b25]',
} as const
