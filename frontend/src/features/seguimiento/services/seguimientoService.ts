/**
 * seguimientoService — wraps GET /api/v1/analisis/monitor for the Seguimiento feature.
 *
 * The backend auto-scopes results by role:
 *   PROFESOR/TUTOR → only their assigned students
 *   COORDINADOR/ADMIN → all students in the tenant
 *
 * All null/undefined filter values are stripped before the request.
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type { SeguimientoFila, SeguimientoParams } from '../types'

/**
 * GET /api/v1/analisis/monitor
 * Returns monitor rows scoped by the caller's role (JWT-verified, server-side).
 */
export async function listarSeguimiento(params: SeguimientoParams): Promise<SeguimientoFila[]> {
  try {
    const query: Record<string, string | number> = {}

    if (params.busqueda != null) query['busqueda'] = params.busqueda
    if (params.comision != null) query['comision'] = params.comision
    if (params.regional != null) query['regional'] = params.regional
    if (params.min_cumplidas != null) query['min_cumplidas'] = params.min_cumplidas

    const response = await apiClient.get<SeguimientoFila[]>('/analisis/monitor', {
      params: query,
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
