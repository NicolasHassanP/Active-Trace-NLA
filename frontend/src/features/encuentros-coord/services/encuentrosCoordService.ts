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
import type { InstanciaEncuentroRead, GuardiaRead, InstanciasParams, GuardiaParams, CrearSlotRequest, CrearSlotResponse } from '../types'

// ---------------------------------------------------------------------------
// crearSlot — POST /api/v1/encuentros/slots
// ---------------------------------------------------------------------------

/**
 * POST /api/v1/encuentros/slots
 * Creates a slot with one or more instancias (recurring or one-time).
 * Identity/tenant from JWT — never in the request body.
 */
export async function crearSlot(payload: CrearSlotRequest): Promise<CrearSlotResponse> {
  try {
    const response = await apiClient.post<CrearSlotResponse>('/encuentros/slots', payload)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

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

// ---------------------------------------------------------------------------
// editarInstancia — PATCH /api/v1/encuentros/instancias/{id}
// ---------------------------------------------------------------------------

export interface EditarInstanciaPayload {
  estado?: 'Programado' | 'Realizado' | 'Cancelado' | null
  meet_url?: string | null
  video_url?: string | null
  comentario?: string | null
}

/**
 * PATCH /api/v1/encuentros/instancias/{id}
 * Edits the mutable fields of an instancia. All fields are optional (partial patch).
 * Identity/tenant from JWT — never in the request body.
 */
export async function editarInstancia(
  id: string,
  payload: EditarInstanciaPayload,
): Promise<InstanciaEncuentroRead> {
  try {
    const response = await apiClient.patch<InstanciaEncuentroRead>(
      `/encuentros/instancias/${id}`,
      payload,
    )
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// borrarInstancia — DELETE /api/v1/encuentros/instancias/{id}
// ---------------------------------------------------------------------------

/**
 * DELETE /api/v1/encuentros/instancias/{id}
 * Deletes an instancia. Returns 204 on success, 404 if not found.
 * Identity/tenant from JWT — never in the request body.
 */
export async function borrarInstancia(id: string): Promise<void> {
  try {
    await apiClient.delete(`/encuentros/instancias/${id}`)
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// getBloqueHtml — GET /api/v1/encuentros/bloque-html
// ---------------------------------------------------------------------------

/**
 * GET /api/v1/encuentros/bloque-html?materia_id=<uuid>
 * Returns pre-formatted HTML ready to paste into Moodle.
 * materia_id is optional; omitting it returns the HTML for all materias.
 */
export async function getBloqueHtml(materia_id?: string | null): Promise<{ html: string }> {
  const params = materia_id ? `?materia_id=${materia_id}` : ''
  const res = await apiClient.get<{ html: string }>(`/encuentros/bloque-html${params}`)
  return res.data
}
