type LoadingStateProps = {
  label: string
}

export function LoadingState({ label }: LoadingStateProps) {
  return (
    <div role="status" className="flex items-center gap-3 px-1 py-4 text-sm text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-petrol motion-reduce:animate-none" />
      {label}
    </div>
  )
}
