/**
 * AuthProvider — React Context provider for session state.
 *
 * Responsibilities:
 * - Rehydrates session on mount via POST /auth/refresh
 * - Exposes user, roles, tenantId, isAuthenticated, isInitializing
 * - Provides login() and logout() actions
 * - Registers logout callback in apiClient for interceptor-forced logouts
 */
import { useState, useEffect, useCallback, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { AuthContext, type LoginParams } from './AuthContext'
import type { AuthUser, Role } from '../types'
import * as authService from '../services/authService'
import * as tokenStore from '@/shared/services/tokenStore'
import { registerLogoutCallback } from '@/shared/services/api'

interface Props {
  children: ReactNode
}

export function AuthProvider({ children }: Props) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isInitializing, setIsInitializing] = useState(true)
  const queryClient = useQueryClient()

  // Derive computed values
  const roles: Role[] = user?.roles ?? []
  const tenantId: string | null = user?.tenantId ?? null
  const isAuthenticated = user !== null

  // ---------- forced logout from interceptor ----------
  const forceLogout = useCallback(() => {
    setUser(null)
    tokenStore.clearAll()
    queryClient.clear()
  }, [queryClient])

  // Register with interceptor once
  useEffect(() => {
    registerLogoutCallback(forceLogout)
  }, [forceLogout])

  // ---------- rehydrate session on mount ----------
  useEffect(() => {
    let cancelled = false

    async function rehydrate() {
      try {
        const { user: hydratedUser } = await authService.refresh()
        if (!cancelled) {
          setUser(hydratedUser)
        }
      } catch {
        // No valid refresh token or refresh failed → unauthenticated
        if (!cancelled) {
          tokenStore.clearAll()
          setUser(null)
        }
      } finally {
        if (!cancelled) {
          setIsInitializing(false)
        }
      }
    }

    void rehydrate()
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ---------- login action ----------
  const login = useCallback(async (params: LoginParams) => {
    const { user: loggedUser } = await authService.login(params)
    setUser(loggedUser)
  }, [])

  // ---------- logout action ----------
  const logout = useCallback(async () => {
    await authService.logout()
    setUser(null)
    queryClient.clear()
  }, [queryClient])

  // ---------- impersonation actions ----------
  const impersonarUsuario = useCallback(async (usuarioId: string) => {
    const { accessToken } = await authService.impersonarUsuario(usuarioId)
    // Build the new AuthUser from the impersonation token
    const { decodeJwtPayload } = await import('../services/decodeJwtPayload')
    const payload = decodeJwtPayload(accessToken)
    if (!payload) throw new Error('Invalid impersonation token received from server')
    setUser({
      id: payload.sub,
      email: payload.email ?? '',
      roles: payload.roles,
      tenantId: payload.tenant_id,
      isImpersonating: !!payload.impersonated_user_id,
      impersonatedName: payload.impersonated_name ?? null,
    })
  }, [])

  const finalizarImpersonacion = useCallback(async () => {
    const { user: restoredUser } = await authService.finalizarImpersonacion()
    setUser(restoredUser)
  }, [])

  // ---------- derived impersonation values ----------
  const isImpersonating = user?.isImpersonating ?? false
  const impersonatedName = user?.impersonatedName ?? null

  return (
    <AuthContext.Provider
      value={{
        user,
        roles,
        tenantId,
        isAuthenticated,
        isInitializing,
        isImpersonating,
        impersonatedName,
        login,
        logout,
        impersonarUsuario,
        finalizarImpersonacion,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
