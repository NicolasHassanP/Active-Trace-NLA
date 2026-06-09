/**
 * Auth services — wraps backend auth endpoints via the centralized Axios client.
 * No GET /auth/me — identity comes from JWT claims (OQ-1 closed).
 */
import axios from 'axios'
import apiClient from '@/shared/services/api'
import * as tokenStore from '@/shared/services/tokenStore'
import type { AuthTokens, AuthUser } from '../types'
import { decodeJwtPayload } from './decodeJwtPayload'

export interface LoginCredentials {
  email: string
  password: string
  tenantId: string
}

/**
 * Access token response — the refresh token is no longer in the body.
 * It travels as an httpOnly cookie set by the server (C-03 transport change).
 */
interface AccessTokenResponse {
  access_token: string
  token_type: string
}

function tokenPairToAuthUser(accessToken: string): AuthUser | null {
  const payload = decodeJwtPayload(accessToken)
  if (!payload) return null
  return {
    id: payload.sub,
    email: payload.email ?? '',
    roles: payload.roles,
    tenantId: payload.tenant_id,
    isImpersonating: !!payload.impersonated_user_id,
    impersonatedName: payload.impersonated_name ?? null,
  }
}

/**
 * Login: POST /auth/login
 * Returns the AuthUser hydrated from the access token claims.
 * The refresh token is NOT in the response body — it arrives as an httpOnly cookie.
 */
export async function login(
  credentials: LoginCredentials,
): Promise<{ tokens: AuthTokens; user: AuthUser }> {
  const response = await apiClient.post<AccessTokenResponse>('/auth/login', {
    email: credentials.email,
    password: credentials.password,
  }, {
    headers: { 'X-Tenant': credentials.tenantId },
  })

  const tokens: AuthTokens = {
    accessToken: response.data.access_token,
    tokenType: response.data.token_type,
  }

  tokenStore.setToken(tokens.accessToken)
  // Refresh token is managed by the browser as an httpOnly cookie — no JS access needed

  const user = tokenPairToAuthUser(tokens.accessToken)
  if (!user) throw new Error('Invalid access token received from server')

  return { tokens, user }
}

/**
 * Refresh: POST /auth/refresh
 * Used for session rehydration on app mount and by the Axios interceptor.
 * No body needed — the refresh token travels as an httpOnly cookie (withCredentials: true).
 * Uses plain axios (not apiClient) to bypass the retry interceptor — avoids
 * infinite loop when called from AuthProvider on mount.
 * Returns AuthUser hydrated from new access token.
 */
export async function refresh(): Promise<{ tokens: AuthTokens; user: AuthUser }> {
  // No body — the httpOnly cookie is sent automatically via withCredentials.
  // Use plain axios (not apiClient) to avoid the 401 → doRefresh → 401 loop.
  const response = await axios.post<AccessTokenResponse>('/api/v1/auth/refresh', undefined, {
    withCredentials: true,
  })

  const tokens: AuthTokens = {
    accessToken: response.data.access_token,
    tokenType: response.data.token_type,
  }

  tokenStore.setToken(tokens.accessToken)
  // Rotated refresh token arrives as a new httpOnly cookie — no JS access needed

  const user = tokenPairToAuthUser(tokens.accessToken)
  if (!user) throw new Error('Invalid access token received from server')

  return { tokens, user }
}

/**
 * Logout: POST /auth/logout
 * Revokes the session on the server. Resilient: clears local state even if call fails.
 * No body needed — the refresh token travels as an httpOnly cookie (withCredentials: true).
 */
export async function logout(): Promise<void> {
  try {
    // No body — the httpOnly cookie is sent automatically via withCredentials
    await apiClient.post('/auth/logout')
  } catch {
    // Resilient logout: clean local state regardless of backend response
  } finally {
    tokenStore.clearAll()
  }
}

/**
 * Impersonar usuario: POST /usuarios/{usuarioId}/impersonar
 * Only callable by ADMIN. Returns a new access token with impersonation claims.
 */
export async function impersonarUsuario(
  usuarioId: string,
): Promise<{ accessToken: string; impersonatedName: string }> {
  const response = await apiClient.post<{ access_token: string; impersonated_name: string }>(
    `/usuarios/${usuarioId}/impersonar`,
  )
  const accessToken = response.data.access_token
  tokenStore.setToken(accessToken)
  return {
    accessToken,
    impersonatedName: response.data.impersonated_name,
  }
}

/**
 * Finalizar impersonación: POST /auth/impersonacion/finalizar
 * Ends an active impersonation session. Returns a clean token (no impersonation claims).
 * The Authorization header is injected automatically by the request interceptor.
 */
export async function finalizarImpersonacion(): Promise<{ user: AuthUser; tokens: AuthTokens }> {
  const response = await apiClient.post<AccessTokenResponse>('/auth/impersonacion/finalizar')

  const tokens: AuthTokens = {
    accessToken: response.data.access_token,
    tokenType: response.data.token_type,
  }

  tokenStore.setToken(tokens.accessToken)

  const user = tokenPairToAuthUser(tokens.accessToken)
  if (!user) throw new Error('Invalid access token received from server')

  return { tokens, user }
}
