/**
 * coloquiosService — wraps C-14 Coloquios API endpoints.
 * Identity/tenant NEVER in request body — travels via JWT (apiClient interceptor).
 * Errors wrapped with parseDomainError for typed handling.
 * Tasks 6.2–6.7.
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type {
  MetricasRead,
  ConvocatoriaMetricasRead,
  ConvocatoriaConTurnosRead,
  AgendaItemRead,
  ResultadoRead,
  CrearConvocatoriaRequest,
  ImportarCandidatosRequest,
} from '../types'

// ---------------------------------------------------------------------------
// Agenda filter params (for GET /coloquios/agenda)
// ---------------------------------------------------------------------------

export interface AgendaParams {
  materia_id?: string | null
  fecha_desde?: string | null
  fecha_hasta?: string | null
}

// ---------------------------------------------------------------------------
// Task 6.2 — metricas
// ---------------------------------------------------------------------------

/**
 * GET /api/v1/coloquios/metricas
 * Returns global metrics panel (F7.1).
 */
export async function metricas(): Promise<MetricasRead> {
  try {
    const response = await apiClient.get<MetricasRead>('/coloquios/metricas')
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Task 6.3 — listarConvocatorias
// ---------------------------------------------------------------------------

/**
 * GET /api/v1/coloquios/convocatorias
 * Returns all convocatorias with derived metrics (F7.4).
 */
export async function listarConvocatorias(): Promise<ConvocatoriaMetricasRead[]> {
  try {
    const response = await apiClient.get<ConvocatoriaMetricasRead[]>('/coloquios/convocatorias')
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Task 6.4 — crearConvocatoria
// ---------------------------------------------------------------------------

/**
 * POST /api/v1/coloquios/convocatorias
 * Creates a convocatoria with its turnos.
 * Returns ConvocatoriaConTurnosRead on 201.
 */
export async function crearConvocatoria(body: CrearConvocatoriaRequest): Promise<ConvocatoriaConTurnosRead> {
  try {
    const response = await apiClient.post<ConvocatoriaConTurnosRead>('/coloquios/convocatorias', body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Task 6.5 — importarCandidatos
// ---------------------------------------------------------------------------

/**
 * POST /api/v1/coloquios/convocatorias/{evaluacion_id}/candidatos
 * Imports the list of candidate alumnos for a convocatoria (idempotent).
 * Returns undefined on 204 (no content).
 */
export async function importarCandidatos(
  evaluacionId: string,
  body: ImportarCandidatosRequest,
): Promise<void> {
  try {
    await apiClient.post(`/coloquios/convocatorias/${evaluacionId}/candidatos`, body)
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Task 6.6 — cerrarConvocatoria
// ---------------------------------------------------------------------------

/**
 * POST /api/v1/coloquios/convocatorias/{evaluacion_id}/cerrar
 * Closes a convocatoria (no new reservas accepted after this).
 * Returns the response body on 200.
 */
export async function cerrarConvocatoria(evaluacionId: string): Promise<unknown> {
  try {
    const response = await apiClient.post<unknown>(`/coloquios/convocatorias/${evaluacionId}/cerrar`)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Task 6.7 — agenda and resultados
// ---------------------------------------------------------------------------

/**
 * GET /api/v1/coloquios/agenda
 * Returns consolidated agenda of active reservas (F7.5).
 * Optional filters: materia_id, fecha_desde, fecha_hasta.
 */
export async function agenda(params: AgendaParams): Promise<AgendaItemRead[]> {
  try {
    const query: Record<string, string> = {}
    if (params.materia_id != null) query['materia_id'] = params.materia_id
    if (params.fecha_desde != null) query['fecha_desde'] = params.fecha_desde
    if (params.fecha_hasta != null) query['fecha_hasta'] = params.fecha_hasta

    const response = await apiClient.get<AgendaItemRead[]>('/coloquios/agenda', { params: query })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * GET /api/v1/coloquios/convocatorias/{evaluacion_id}/resultados
 * Returns academic results for all alumnos in a convocatoria.
 */
export async function resultados(evaluacionId: string): Promise<ResultadoRead[]> {
  try {
    const response = await apiClient.get<ResultadoRead[]>(
      `/coloquios/convocatorias/${evaluacionId}/resultados`,
    )
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
