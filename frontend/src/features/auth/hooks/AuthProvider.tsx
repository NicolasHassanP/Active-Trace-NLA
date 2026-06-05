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

  return (
    <AuthContext.Provider
      value={{
        user,
        roles,
        tenantId,
        isAuthenticated,
        isInitializing,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
