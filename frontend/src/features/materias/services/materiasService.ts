/**
 * materiasService — wraps the mis-equipos endpoint for the Materias feature (F4.2).
 * Identity/tenant never in request body — they travel via JWT (apiClient interceptor).
 * Errors are wrapped with parseDomainError for typed handling.
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type { MisMateriasItem } from '../types'

/**
 * GET /api/v1/equipos/mis-equipos
 * Returns the authenticated user's assignments with estado_vigencia.
 * Used by the Materias page (F4.2 — Vista de mis equipos).
 */
export async function listarMisMaterias(): Promise<MisMateriasItem[]> {
  try {
    const response = await apiClient.get<MisMateriasItem[]>('/equipos/mis-equipos')
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
