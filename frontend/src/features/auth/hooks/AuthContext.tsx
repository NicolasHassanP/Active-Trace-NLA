import { createContext } from 'react'
import type { AuthUser, Role } from '../types'

export interface LoginParams {
  email: string
  password: string
  tenantId: string
}

export interface AuthContextValue {
  user: AuthUser | null
  roles: Role[]
  tenantId: string | null
  isAuthenticated: boolean
  /** True while the initial session rehydration is in progress (prevents guard redirects) */
  isInitializing: boolean
  /** True when the current session is an admin impersonating another user */
  isImpersonating: boolean
  /** Display name of the impersonated user, or null when not impersonating */
  impersonatedName: string | null
  login: (params: LoginParams) => Promise<void>
  logout: () => Promise<void>
  /** Start impersonating a user (ADMIN only). Replaces the active token. */
  impersonarUsuario: (usuarioId: string) => Promise<void>
  /** End the current impersonation session and restore the admin token. */
  finalizarImpersonacion: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
