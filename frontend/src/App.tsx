import { BrowserRouter, Route, Routes } from 'react-router'
import { AuthProvider, RequireAuth } from './auth.tsx'
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
import { DealCreatePage, DealEditPage } from './pages/deals/DealFormPage.tsx'
import { DealDetailPage } from './pages/deals/DealDetailPage.tsx'
import { DealListPage } from './pages/deals/DealListPage.tsx'
import { PipelinePage } from './pages/deals/PipelinePage.tsx'
import { OrderCreatePage, OrderEditPage } from './pages/orders/OrderFormPage.tsx'
import { OrderDetailPage } from './pages/orders/OrderDetailPage.tsx'
import { OrderListPage } from './pages/orders/OrderListPage.tsx'
import { ProductCreatePage, ProductEditPage } from './pages/products/ProductFormPage.tsx'
import { ProductListPage } from './pages/products/ProductListPage.tsx'
import { SegmentCreatePage, SegmentDetailPage, SegmentEditPage, SegmentListPage } from './pages/segments/SegmentPages.tsx'
import { TicketCreatePage, TicketEditPage } from './pages/service/TicketFormPage.tsx'
import { TicketDetailPage } from './pages/service/TicketDetailPage.tsx'
import { TicketListPage } from './pages/service/TicketListPage.tsx'
import { AutomationDetailPage, AutomationFormPage, AutomationListPage } from './pages/automations/AutomationPages.tsx'
import { CampaignDetailPage, CampaignFormPage, CampaignListPage } from './pages/campaigns/CampaignPages.tsx'
import { TemplateDetailPage, TemplateFormPage, TemplateListPage } from './pages/campaigns/TemplatePages.tsx'
import { CarePage } from './pages/care/CarePage.tsx'
import { NotificationCenterPage, NotificationSettingsPage } from './pages/notifications/NotificationPages.tsx'
import { SettingsPage } from './pages/SettingsPage.tsx'
import { LoginPage } from './pages/auth/LoginPage.tsx'
import { ProfilePage } from './pages/auth/ProfilePage.tsx'
import { ResetPage } from './pages/auth/ResetPage.tsx'
import { ReportingPage } from './pages/reporting/ReportingPage.tsx'
import { AuditPage, RolesPage, UserCreatePage, UserDetailPage, UserListPage } from './pages/users/UserPages.tsx'

export default function App() {
  const modules = navigation.filter((item) => item.phase === 'planned')

  return (
    <ErrorBoundary>
      <ToastProvider>
        <BrowserRouter>
          <AuthProvider>
          <Routes>
            <Route path="/anmelden" element={<LoginPage />} />
            <Route path="/passwort-zuruecksetzen" element={<ResetPage />} />
            <Route element={<RequireAuth />}>
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
              <Route path="verkaufschancen/neu" element={<DealCreatePage />} />
              <Route path="verkaufschancen/pipeline" element={<PipelinePage />} />
              <Route path="verkaufschancen/:dealId/bearbeiten" element={<DealEditPage />} />
              <Route path="verkaufschancen/:dealId" element={<DealDetailPage />} />
              <Route path="verkaufschancen" element={<DealListPage />} />
              <Route path="produkte/neu" element={<ProductCreatePage />} />
              <Route path="produkte/:productId/bearbeiten" element={<ProductEditPage />} />
              <Route path="produkte" element={<ProductListPage />} />
              <Route path="bestellungen/neu" element={<OrderCreatePage />} />
              <Route path="bestellungen/:orderId/bearbeiten" element={<OrderEditPage />} />
              <Route path="bestellungen/:orderId" element={<OrderDetailPage />} />
              <Route path="bestellungen" element={<OrderListPage />} />
              <Route path="kundenservice/neu" element={<TicketCreatePage />} />
              <Route path="kundenservice/:ticketId/bearbeiten" element={<TicketEditPage />} />
              <Route path="kundenservice/:ticketId" element={<TicketDetailPage />} />
              <Route path="kundenservice" element={<TicketListPage />} />
              <Route path="segmente/neu" element={<SegmentCreatePage />} />
              <Route path="segmente/:segmentId/bearbeiten" element={<SegmentEditPage />} />
              <Route path="segmente/:segmentId" element={<SegmentDetailPage />} />
              <Route path="segmente" element={<SegmentListPage />} />
              <Route path="kampagnen/vorlagen/neu" element={<TemplateFormPage />} />
              <Route path="kampagnen/vorlagen/:templateId/bearbeiten" element={<TemplateFormPage />} />
              <Route path="kampagnen/vorlagen/:templateId" element={<TemplateDetailPage />} />
              <Route path="kampagnen/vorlagen" element={<TemplateListPage />} />
              <Route path="kampagnen/neu" element={<CampaignFormPage />} />
              <Route path="kampagnen/:campaignId/bearbeiten" element={<CampaignFormPage />} />
              <Route path="kampagnen/:campaignId" element={<CampaignDetailPage />} />
              <Route path="kampagnen" element={<CampaignListPage />} />
              <Route path="partnerbetreuung" element={<CarePage />} />
              <Route path="automatisierungen/neu" element={<AutomationFormPage />} />
              <Route path="automatisierungen/:ruleId/bearbeiten" element={<AutomationFormPage />} />
              <Route path="automatisierungen/:ruleId/protokoll" element={<AutomationDetailPage />} />
              <Route path="automatisierungen/:ruleId" element={<AutomationDetailPage />} />
              <Route path="automatisierungen" element={<AutomationListPage />} />
              <Route path="benachrichtigungen/einstellungen" element={<NotificationSettingsPage />} />
              <Route path="benachrichtigungen" element={<NotificationCenterPage />} />
              <Route path="reporting" element={<ReportingPage />} />
              <Route path="profil" element={<ProfilePage />} />
              <Route path="benutzer/neu" element={<UserCreatePage />} />
              <Route path="benutzer/rollen" element={<RolesPage />} />
              <Route path="benutzer/protokoll" element={<AuditPage />} />
              <Route path="benutzer/:userId" element={<UserDetailPage />} />
              <Route path="benutzer" element={<UserListPage />} />
              {modules.map((item) => (
                <Route key={item.id} path={item.path.slice(1)} element={<ModulePage item={item} />} />
              ))}
              <Route path="einstellungen" element={<SettingsPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
            </Route>
          </Routes>
          </AuthProvider>
        </BrowserRouter>
      </ToastProvider>
    </ErrorBoundary>
  )
}
