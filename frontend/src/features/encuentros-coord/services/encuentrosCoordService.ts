/**
 * encuentrosCoordService — wraps C-13 Encuentros and Guardias API endpoints.
 * Identity/tenant never in request body — travels via JWT (apiClient interceptor).
 * Errors wrapped with parseDomainError for typed handling.
 *
 * OQ-4 RESOLVED:
 *   GET /encuentros/instancias → filter: materia_id (optional UUID)
 *   GET /guardias              → filters: materia_id, carrera_id, cohorte_id, dia, estado (all optional)
 *   GET /guardias/export       → same filters, returns CSV Blob attachment
 *
 * Tasks 5.2, 5.3, 5.4.
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type { InstanciaEncuentroRead, GuardiaRead, InstanciasParams, GuardiaParams } from '../types'

// ---------------------------------------------------------------------------
// Task 5.2 — listarInstancias
// ---------------------------------------------------------------------------

/**
 * GET /api/v1/encuentros/instancias
 * Returns all instancias for the tenant (COORDINADOR/ADMIN: all; PROFESOR: own).
 * Accepts optional materia_id filter.
 */
export async function listarInstancias(params: InstanciasParams): Promise<InstanciaEncuentroRead[]> {
  try {
    const query: Record<string, string> = {}
    if (params.materia_id != null) query['materia_id'] = params.materia_id

    const response = await apiClient.get<InstanciaEncuentroRead[]>('/encuentros/instancias', {
      params: query,
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Task 5.3 — listarGuardias
// ---------------------------------------------------------------------------

/**
 * GET /api/v1/guardias
 * Returns guardias filtered by the provided params.
 * Filters: materia_id, carrera_id, cohorte_id, dia, estado — all optional.
 */
export async function listarGuardias(params: GuardiaParams): Promise<GuardiaRead[]> {
  try {
    const query: Record<string, string> = {}
    if (params.materia_id != null) query['materia_id'] = params.materia_id
    if (params.carrera_id != null) query['carrera_id'] = params.carrera_id
    if (params.cohorte_id != null) query['cohorte_id'] = params.cohorte_id
    if (params.dia != null) query['dia'] = params.dia
    if (params.estado != null) query['estado'] = params.estado

    const response = await apiClient.get<GuardiaRead[]>('/guardias', { params: query })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Task 5.4 — exportarGuardias
// ---------------------------------------------------------------------------

/**
 * GET /api/v1/guardias/export
 * Returns a CSV Blob attachment for the filtered guardias.
 * Caller uses downloadFile() from @/shared/services/downloadFile to trigger download.
 * Same filters as listarGuardias: materia_id, carrera_id, cohorte_id, dia, estado.
 */
export async function exportarGuardias(params: GuardiaParams): Promise<Blob> {
  try {
    const query: Record<string, string> = {}
    if (params.materia_id != null) query['materia_id'] = params.materia_id
    if (params.carrera_id != null) query['carrera_id'] = params.carrera_id
    if (params.cohorte_id != null) query['cohorte_id'] = params.cohorte_id
    if (params.dia != null) query['dia'] = params.dia
    if (params.estado != null) query['estado'] = params.estado

    const response = await apiClient.get<Blob>('/guardias/export', {
      responseType: 'blob',
      params: query,
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
