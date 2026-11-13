import { useState, type ReactNode } from 'react'
import { cx } from '../../lib/cx.ts'
import { ToastContext, type ToastMessage, type ToastTone } from './toast-state.ts'

const tones: Record<ToastTone, string> = {
  success: 'border-success bg-success-soft',
  warning: 'border-warning bg-warning-soft',
  critical: 'border-critical bg-critical-soft',
  info: 'border-petrol bg-petrol-soft',
}

type ToastProviderProps = {
  children: ReactNode
}

export function ToastProvider({ children }: ToastProviderProps) {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  function dismiss(id: string) {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }

  function notify(toast: { tone: ToastTone; message: string }) {
    const id = crypto.randomUUID()
    setToasts((current) => [...current, { id, tone: toast.tone, message: toast.message }])
    window.setTimeout(() => dismiss(id), 6000)
  }

  return (
    <ToastContext.Provider value={{ notify }}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed right-4 bottom-4 left-4 z-50 grid justify-items-end gap-2 sm:left-auto sm:w-96">
        {toasts.map((toast) => (
          <div key={toast.id} className={cx('pointer-events-auto w-full border px-4 py-3 text-sm shadow-md', tones[toast.tone])}>
            <div className="flex items-start justify-between gap-3">
              <p>{toast.message}</p>
              <button type="button" className="font-semibold" onClick={() => dismiss(toast.id)}>
                Schliessen
              </button>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
