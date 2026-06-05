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
  login: (params: LoginParams) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
