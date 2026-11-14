import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

const originalFetch = window.fetch.bind(window)
window.fetch = (input, init) => {
  const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
  if (!url.startsWith('/api')) {
    return originalFetch(input, init)
  }
  const headers = new Headers(init?.headers)
  const method = (init?.method ?? 'GET').toUpperCase()
  if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') {
    const raw = document.cookie
      .split('; ')
      .find((row) => row.startsWith('bp_csrf='))
      ?.slice('bp_csrf='.length)
    if (raw) {
      headers.set('X-CSRF-Token', decodeURIComponent(raw))
    }
  }
  return originalFetch(input, { ...init, credentials: 'include', headers })
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
