/**
 * Domain types for authentication.
 * Role union matches the backend RBAC model (C-04).
 */

export type Role =
  | 'ALUMNO'
  | 'TUTOR'
  | 'PROFESOR'
  | 'COORDINADOR'
  | 'NEXO'
  | 'ADMIN'
  | 'FINANZAS'

/**
 * Authenticated user identity — hydrated from the JWT access token claims.
 * Claims: sub (user_id), tenant_id, roles, exp, email.
 */
export interface AuthUser {
  id: string
  email: string
  roles: Role[]
  tenantId: string
  /** Display name — may be absent in minimal JWT implementations */
  name?: string
  /** True when an ADMIN is viewing the session as another user */
  isImpersonating: boolean
  /** Display name of the impersonated user, or null when not impersonating */
  impersonatedName: string | null
}

/**
 * Access token returned by login and refresh endpoints.
 * Kept in memory (never localStorage).
 * The refresh token travels as an httpOnly cookie — never exposed to JS (C-03 transport change).
 */
export interface AuthTokens {
  accessToken: string
  tokenType: string
}

/**
 * JWT payload claims decoded from the access token.
 * sub = user_id (UUID), tenant_id, roles, exp (Unix timestamp).
 * When impersonation is active, the ADMIN's sub is in sub and the target
 * user info is carried in impersonated_user_id / impersonated_name.
 */
export interface JwtPayload {
  sub: string
  tenant_id: string
  roles: Role[]
  exp: number
  email?: string
  /** Present only when an ADMIN is impersonating another user */
  impersonated_user_id?: string
  /** Display name of the impersonated user */
  impersonated_name?: string
}
