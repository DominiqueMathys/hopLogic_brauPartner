import { createContext, useContext } from 'react'

export type ToastTone = 'success' | 'warning' | 'critical' | 'info'

export type ToastMessage = {
  id: string
  tone: ToastTone
  message: string
}

export type ToastContextValue = {
  notify: (toast: { tone: ToastTone; message: string }) => void
}

export const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast(): ToastContextValue {
  const value = useContext(ToastContext)
  if (!value) {
    throw new Error('useToast muss innerhalb von ToastProvider stehen.')
  }
  return value
}
