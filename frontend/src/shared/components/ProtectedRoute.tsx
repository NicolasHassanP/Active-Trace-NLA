/**
 * ProtectedRoute — guards private routes.
 *
 * Behavior:
 * - isInitializing → show spinner (prevents premature redirect before session resolves)
 * - not authenticated → redirect to /login with state.from = current location
 * - authenticated, but missing required role → show Forbidden403
 * - authenticated, role OK → render <Outlet />
 *
 * Fail-closed: no role match → 403.
 */
import { type ReactNode } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/features/auth/hooks/useAuth'
import type { Role } from '@/features/auth/types'
import Forbidden403 from './Forbidden403'

interface Props {
  requiredRoles?: Role[]
  children?: ReactNode
}

export default function ProtectedRoute({ requiredRoles, children }: Props) {
  const { isAuthenticated, isInitializing, roles } = useAuth()
  const location = useLocation()

  if (isInitializing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div role="status" aria-label="Cargando sesión" className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        state={{ from: location.pathname }}
        replace
      />
    )
  }

  if (requiredRoles && requiredRoles.length > 0) {
    const hasRole = requiredRoles.some((r) => roles.includes(r))
    if (!hasRole) {
      return <Forbidden403 />
    }
  }

  return children ? <>{children}</> : <Outlet />
}
