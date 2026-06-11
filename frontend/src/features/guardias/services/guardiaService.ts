/**
 * guardiaService — wraps the Guardias API endpoints (backend/app/api/v1/routers/guardias.py).
 * All endpoints require the 'encuentros:gestionar' permission.
 * Identity/tenant never in the request body — they travel via JWT (apiClient interceptor).
 * Errors are wrapped with parseDomainError for typed handling.
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type { GuardiaRead, RegistrarGuardiaRequest, GuardiaFiltros } from '../types'

/** Builds a query object from the filtros, omitting null/undefined values. */
function filtrosToParams(filtros: GuardiaFiltros): Record<string, string> {
  const params: Record<string, string> = {}
  if (filtros.materia_id != null) params['materia_id'] = filtros.materia_id
  if (filtros.carrera_id != null) params['carrera_id'] = filtros.carrera_id
  if (filtros.cohorte_id != null) params['cohorte_id'] = filtros.cohorte_id
  if (filtros.dia != null) params['dia'] = filtros.dia
  if (filtros.estado != null) params['estado'] = filtros.estado
  return params
}

/**
 * POST /api/v1/guardias
 * Registers a guardia. asignacion_id/tenant_id resolved from the JWT — never in the body.
 * Returns the created GuardiaRead on 201.
 */
export async function registrarGuardia(body: RegistrarGuardiaRequest): Promise<GuardiaRead> {
  try {
    const response = await apiClient.post<GuardiaRead>('/guardias', body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * GET /api/v1/guardias
 * Returns guardias filtered by the provided filtros (role-scoped on the backend).
 * Filters: materia_id, carrera_id, cohorte_id, dia, estado — all optional.
 */
export async function listarGuardias(filtros: GuardiaFiltros): Promise<GuardiaRead[]> {
  try {
    const response = await apiClient.get<GuardiaRead[]>('/guardias', {
      params: filtrosToParams(filtros),
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * GET /api/v1/guardias/export
 * Returns a CSV Blob attachment for the filtered guardias.
 * Caller uses downloadFile() from @/shared/services/downloadFile to trigger the download.
 */
export async function exportarGuardias(filtros: GuardiaFiltros): Promise<Blob> {
  try {
    const response = await apiClient.get<Blob>('/guardias/export', {
      responseType: 'blob',
      params: filtrosToParams(filtros),
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
