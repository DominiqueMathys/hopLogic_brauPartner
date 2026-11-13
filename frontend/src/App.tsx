import { BrowserRouter, Route, Routes } from 'react-router'
import { ErrorBoundary } from './components/ErrorBoundary.tsx'
import { AppShell } from './components/layout/AppShell.tsx'
import { ToastProvider } from './components/ui/ToastNotification.tsx'
import { navigation } from './navigation.ts'
import { DashboardPage } from './pages/DashboardPage.tsx'
import { ModulePage } from './pages/ModulePage.tsx'
import { NotFoundPage } from './pages/NotFoundPage.tsx'
import { SettingsPage } from './pages/SettingsPage.tsx'

export default function App() {
  const modules = navigation.filter((item) => item.phase === 'planned')

  return (
    <ErrorBoundary>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<DashboardPage />} />
              {modules.map((item) => (
                <Route key={item.id} path={item.path.slice(1)} element={<ModulePage item={item} />} />
              ))}
              <Route path="einstellungen" element={<SettingsPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </ErrorBoundary>
  )
}
