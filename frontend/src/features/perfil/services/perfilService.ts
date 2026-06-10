/**
 * perfilService — wraps the self-profile API (GET / PATCH /api/v1/perfil).
 * Identity/tenant never travel in the request body — the backend resolves the user
 * from the JWT (apiClient interceptor). The PATCH body carries ONLY editable fields.
 * Errors are wrapped with parseDomainError for typed handling (401/403/409/422).
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type { PerfilRead, PerfilUpdate } from '../types'

/**
 * GET /api/v1/perfil
 * Returns the authenticated user's own profile (identity from JWT).
 */
export async function getPerfil(): Promise<PerfilRead> {
  try {
    const response = await apiClient.get<PerfilRead>('/perfil')
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * PATCH /api/v1/perfil
 * Partial update of the authenticated user's own editable fields.
 * `body` must contain only declared PerfilUpdate fields (backend uses extra='forbid').
 */
export async function updatePerfil(body: PerfilUpdate): Promise<PerfilRead> {
  try {
    const response = await apiClient.patch<PerfilRead>('/perfil', body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
