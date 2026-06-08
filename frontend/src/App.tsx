/**
 * App.tsx — root component.
 *
 * Provider hierarchy:
 *   QueryClientProvider → BrowserRouter → AuthProvider → Routes
 *
 * Route structure:
 *   /login          → LoginPage (public)
 *   /               → ProtectedRoute + AppLayout
 *     /dashboard    → DashboardPlaceholder (lazy)
 *     /*            → NotFound404
 *   /* (catch-all)  → NotFound404
 *
 * C-22/C-23/C-24 add their routes inside the protected slot:
 *   <Route path="/materias" element={<React.lazy(...) />} />
 */
import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { AuthProvider } from '@/features/auth/hooks/AuthProvider'
import ProtectedRoute from '@/shared/components/ProtectedRoute'
import AppLayout from '@/features/shell/components/AppLayout'

// Lazy-loaded pages (code splitting)
const LoginPage = lazy(() => import('@/features/auth/components/LoginPage'))
const DashboardPlaceholder = lazy(() => import('@/shared/components/DashboardPlaceholder'))
const NotFound404 = lazy(() => import('@/shared/components/NotFound404'))

// C-22 lazy pages
const PadronPage = lazy(() => import('@/features/padron/pages/PadronPage'))
const AtrasadosPage = lazy(() => import('@/features/atrasados/pages/AtrasadosPage'))
const ComunicacionesPage = lazy(() => import('@/features/comunicaciones/pages/ComunicacionesPage'))

// Calificaciones lazy page (C-22 backfill)
const CalificacionesPage = lazy(() => import('@/features/calificaciones/pages/CalificacionesPage'))

// Seguimiento lazy page (F2.8 — Monitor de seguimiento TUTOR/PROFESOR)
const SeguimientoPage = lazy(() => import('@/features/seguimiento/pages/SeguimientoPage'))

// C-26 lazy pages
const InboxPage = lazy(() => import('@/features/mensajeria/pages/InboxPage'))

// C-25 lazy pages
const MiCursadaPage = lazy(() => import('@/features/mi-cursada/pages/MiCursadaPage'))

// HU-47 lazy pages
const MisColoquiosPage = lazy(() => import('@/features/mis-coloquios/pages/MisColoquiosPage'))

// C-23 lazy pages
const EquiposPage = lazy(() => import('@/features/equipos/pages/EquiposPage'))
const MateriasPage = lazy(() => import('@/features/materias/pages/MateriasPage'))
const AvisosPage = lazy(() => import('@/features/avisos/pages/AvisosPage'))
const TareasPage = lazy(() => import('@/features/tareas/pages/TareasPage'))
const MonitorPage = lazy(() => import('@/features/monitores/pages/MonitorPage'))
const EncuentrosPage = lazy(() => import('@/features/encuentros-coord/pages/EncuentrosPage'))
const ColoquiosPage = lazy(() => import('@/features/coloquios/pages/ColoquiosPage'))
const SetupCuatrimestrePage = lazy(
  () => import('@/features/setup-cuatrimestre/pages/SetupCuatrimestrePage'),
)

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 1000 * 60 * 5, // 5 min
    },
  },
})

const PageFallback = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <div
      role="status"
      aria-label="Cargando página"
      className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"
    />
  </div>
)

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Toaster richColors position="top-right" closeButton duration={6000} />
      <BrowserRouter>
        <AuthProvider>
          <Suspense fallback={<PageFallback />}>
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<LoginPage />} />

              {/* Protected routes — wrapped by ProtectedRoute + AppLayout */}
              <Route element={<ProtectedRoute />}>
                <Route element={<AppLayout />}>
                  <Route index element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<DashboardPlaceholder />} />
                  {/* === C-22 routes === */}
                  <Route
                    path="/padron"
                    element={
                      <ProtectedRoute requiredRoles={['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN']}>
                        <PadronPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/materias/:materiaId/cohortes/:cohorteId/atrasados"
                    element={
                      <ProtectedRoute requiredRoles={['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN']}>
                        <AtrasadosPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/atrasados"
                    element={
                      <ProtectedRoute requiredRoles={['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN']}>
                        <AtrasadosPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/comunicaciones"
                    element={
                      <ProtectedRoute requiredRoles={['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN']}>
                        <ComunicacionesPage />
                      </ProtectedRoute>
                    }
                  />
                  {/* === Calificaciones route (C-22 backfill) === */}
                  <Route
                    path="/calificaciones"
                    element={
                      <ProtectedRoute requiredRoles={['PROFESOR', 'COORDINADOR', 'ADMIN']}>
                        <CalificacionesPage />
                      </ProtectedRoute>
                    }
                  />
                  {/* === C-23 routes === */}
                  {/* /equipos — COORDINADOR/ADMIN for management; PROFESOR/TUTOR/NEXO for mis-equipos (page decides render) */}
                  <Route
                    path="/equipos"
                    element={
                      <ProtectedRoute requiredRoles={['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN', 'NEXO']}>
                        <EquiposPage />
                      </ProtectedRoute>
                    }
                  />
                  {/* /materias — F4.2 Vista de mis equipos: PROFESOR/TUTOR/COORDINADOR/ADMIN/NEXO */}
                  <Route
                    path="/materias"
                    element={
                      <ProtectedRoute requiredRoles={['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN', 'NEXO']}>
                        <MateriasPage />
                      </ProtectedRoute>
                    }
                  />
                  {/* /avisos — any authenticated user (bandeja); management gated inside page */}
                  <Route
                    path="/avisos"
                    element={
                      <ProtectedRoute requiredRoles={['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN', 'NEXO', 'ALUMNO', 'FINANZAS']}>
                        <AvisosPage />
                      </ProtectedRoute>
                    }
                  />
                  {/* /tareas — TUTOR/PROFESOR/COORDINADOR/ADMIN; admin panel gated inside page */}
                  <Route
                    path="/tareas"
                    element={
                      <ProtectedRoute requiredRoles={['TUTOR', 'PROFESOR', 'COORDINADOR', 'ADMIN']}>
                        <TareasPage />
                      </ProtectedRoute>
                    }
                  />
                  {/* /monitor — COORDINADOR/ADMIN only */}
                  <Route
                    path="/monitor"
                    element={
                      <ProtectedRoute requiredRoles={['COORDINADOR', 'ADMIN']}>
                        <MonitorPage />
                      </ProtectedRoute>
                    }
                  />
                  {/* /encuentros — PROFESOR/TUTOR/COORDINADOR/ADMIN */}
                  <Route
                    path="/encuentros"
                    element={
                      <ProtectedRoute requiredRoles={['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN']}>
                        <EncuentrosPage />
                      </ProtectedRoute>
                    }
                  />
                  {/* /coloquios — COORDINADOR/ADMIN gestión; ALUMNO reserva (gating inside page) */}
                  <Route
                    path="/coloquios"
                    element={
                      <ProtectedRoute requiredRoles={['COORDINADOR', 'ADMIN', 'ALUMNO']}>
                        <ColoquiosPage />
                      </ProtectedRoute>
                    }
                  />
                  {/* /setup-cuatrimestre — COORDINADOR/ADMIN only */}
                  <Route
                    path="/setup-cuatrimestre"
                    element={
                      <ProtectedRoute requiredRoles={['COORDINADOR', 'ADMIN']}>
                        <SetupCuatrimestrePage />
                      </ProtectedRoute>
                    }
                  />
                  {/* /seguimiento — F2.8 Monitor de seguimiento TUTOR/PROFESOR/COORD/ADMIN */}
                  <Route
                    path="/seguimiento"
                    element={
                      <ProtectedRoute requiredRoles={['TUTOR', 'PROFESOR', 'COORDINADOR', 'ADMIN']}>
                        <SeguimientoPage />
                      </ProtectedRoute>
                    }
                  />
                  {/* === C-26 routes === */}
                  <Route
                    path="/mensajes"
                    element={
                      <ProtectedRoute requiredRoles={['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN']}>
                        <InboxPage />
                      </ProtectedRoute>
                    }
                  />
                  {/* === C-25 routes === */}
                  <Route
                    path="/mi-cursada"
                    element={
                      <ProtectedRoute requiredRoles={['ALUMNO']}>
                        <MiCursadaPage />
                      </ProtectedRoute>
                    }
                  />
                  {/* === HU-47 routes === */}
                  <Route
                    path="/mis-coloquios"
                    element={
                      <ProtectedRoute requiredRoles={['ALUMNO']}>
                        <MisColoquiosPage />
                      </ProtectedRoute>
                    }
                  />
                  {/* === End C-23 routes === */}
                  <Route path="*" element={<NotFound404 />} />
                </Route>
              </Route>

              {/* Catch-all */}
              <Route path="*" element={<NotFound404 />} />
            </Routes>
          </Suspense>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
