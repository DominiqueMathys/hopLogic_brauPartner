import { BrowserRouter, Route, Routes } from 'react-router'
import { ErrorBoundary } from './components/ErrorBoundary.tsx'
import { AppShell } from './components/layout/AppShell.tsx'
import { ToastProvider } from './components/ui/ToastNotification.tsx'
import { navigation } from './navigation.ts'
import { DashboardPage } from './pages/DashboardPage.tsx'
import { ModulePage } from './pages/ModulePage.tsx'
import { NotFoundPage } from './pages/NotFoundPage.tsx'
import { ActivityCreatePage, ActivityEditPage } from './pages/activities/ActivityFormPage.tsx'
import { ActivityListPage } from './pages/activities/ActivityListPage.tsx'
import { ContactCreatePage } from './pages/contacts/ContactCreatePage.tsx'
import { ContactDetailPage } from './pages/contacts/ContactDetailPage.tsx'
import { ContactEditPage } from './pages/contacts/ContactEditPage.tsx'
import { ContactListPage } from './pages/contacts/ContactListPage.tsx'
import { PartnerCreatePage } from './pages/partners/PartnerCreatePage.tsx'
import { PartnerDetailPage } from './pages/partners/PartnerDetailPage.tsx'
import { PartnerEditPage } from './pages/partners/PartnerEditPage.tsx'
import { PartnerListPage } from './pages/partners/PartnerListPage.tsx'
import { TaskCreatePage, TaskEditPage } from './pages/tasks/TaskFormPage.tsx'
import { TaskListPage } from './pages/tasks/TaskListPage.tsx'
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
              <Route path="vertriebspartner/neu" element={<PartnerCreatePage />} />
              <Route path="vertriebspartner/:partnerId/bearbeiten" element={<PartnerEditPage />} />
              <Route path="vertriebspartner/:partnerId" element={<PartnerDetailPage />} />
              <Route path="vertriebspartner" element={<PartnerListPage />} />
              <Route path="kontakte/neu" element={<ContactCreatePage />} />
              <Route path="kontakte/:contactId/bearbeiten" element={<ContactEditPage />} />
              <Route path="kontakte/:contactId" element={<ContactDetailPage />} />
              <Route path="kontakte" element={<ContactListPage />} />
              <Route path="aktivitaeten/neu" element={<ActivityCreatePage />} />
              <Route path="aktivitaeten/:activityId/bearbeiten" element={<ActivityEditPage />} />
              <Route path="aktivitaeten" element={<ActivityListPage />} />
              <Route path="aufgaben/neu" element={<TaskCreatePage />} />
              <Route path="aufgaben/:taskId/bearbeiten" element={<TaskEditPage />} />
              <Route path="aufgaben" element={<TaskListPage />} />
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
