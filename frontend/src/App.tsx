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
      <Toaster richColors position="top-right" />
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
                  {/* === End C-22 routes === */}
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
