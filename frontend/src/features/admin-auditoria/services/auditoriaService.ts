/**
 * auditoriaService — read-only service for audit panel endpoints.
 * All endpoints require auditoria:ver permission → ADMIN.
 * Identity/tenant never in the request body — they travel via JWT.
 * No mutations (read-only contract from spec).
 * Errors wrapped with parseDomainError.
 *
 * Endpoints:
 *   GET /api/v1/auditoria                                   — list events (paginated)
 *   GET /api/v1/auditoria/metricas/acciones-por-dia        — time series
 *   GET /api/v1/auditoria/metricas/interacciones-docente   — per-actor aggregates
 *   GET /api/v1/auditoria/metricas/interacciones-docente-materia
 *   GET /api/v1/auditoria/metricas/comunicaciones-por-docente
 *   GET /api/v1/auditoria/ultimas-acciones                 — recent events
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type {
  AuditEventRead,
  AuditoriaFiltros,
  MetricaFiltros,
  AccionesPorDiaResponse,
  InteraccionesDocenteResponse,
  InteraccionesDocenteMateriaResponse,
  ComunicacionesPorDocenteResponse,
  UltimaAccionItem,
} from '../types'

/** Builds query params, omitting null/undefined/empty values. */
function toParams(obj: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined && v !== null && v !== '') {
      result[k] = v
    }
  }
  return Object.keys(result).length > 0 ? result : undefined as unknown as Record<string, unknown>
}

// ---------------------------------------------------------------------------
// GET /api/v1/auditoria — list events (paginated)
// ---------------------------------------------------------------------------

/**
 * Lists audit events for the current tenant.
 * Pagination by limit/offset; no total count from backend.
 */
export async function listarEventos(filtros: AuditoriaFiltros): Promise<AuditEventRead[]> {
  try {
    const params = toParams({
      limit: filtros.limit,
      offset: filtros.offset,
      desde: filtros.desde,
      hasta: filtros.hasta,
      actor_user_id: filtros.actor_user_id,
    })
    const response = await apiClient.get<AuditEventRead[]>('/auditoria', { params })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Metrics endpoints — read-only, no auto-audit (C-19 D6)
// ---------------------------------------------------------------------------

/**
 * GET /api/v1/auditoria/metricas/acciones-por-dia
 * Time series of actions grouped by calendar day.
 */
export async function getAccionesPorDia(filtros: MetricaFiltros): Promise<AccionesPorDiaResponse> {
  try {
    const params = toParams({
      desde: filtros.desde,
      hasta: filtros.hasta,
      actor_user_id: filtros.actor_user_id,
      materia_id: filtros.materia_id,
    })
    const response = await apiClient.get<AccionesPorDiaResponse>(
      '/auditoria/metricas/acciones-por-dia',
      { params },
    )
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * GET /api/v1/auditoria/metricas/interacciones-docente
 * Per-actor, per-action aggregates.
 */
export async function getInteraccionesDocente(filtros: MetricaFiltros): Promise<InteraccionesDocenteResponse> {
  try {
    const params = toParams({
      desde: filtros.desde,
      hasta: filtros.hasta,
      actor_user_id: filtros.actor_user_id,
    })
    const response = await apiClient.get<InteraccionesDocenteResponse>(
      '/auditoria/metricas/interacciones-docente',
      { params },
    )
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * GET /api/v1/auditoria/metricas/interacciones-docente-materia
 */
export async function getInteraccionesDocenteMateria(filtros: MetricaFiltros): Promise<InteraccionesDocenteMateriaResponse> {
  try {
    const params = toParams({
      desde: filtros.desde,
      hasta: filtros.hasta,
      actor_user_id: filtros.actor_user_id,
      materia_id: filtros.materia_id,
    })
    const response = await apiClient.get<InteraccionesDocenteMateriaResponse>(
      '/auditoria/metricas/interacciones-docente-materia',
      { params },
    )
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * GET /api/v1/auditoria/metricas/comunicaciones-por-docente
 */
export async function getComunicacionesPorDocente(
  estado?: string,
): Promise<ComunicacionesPorDocenteResponse> {
  try {
    const params = toParams({ estado })
    const response = await apiClient.get<ComunicacionesPorDocenteResponse>(
      '/auditoria/metricas/comunicaciones-por-docente',
      { params },
    )
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// GET /api/v1/auditoria/ultimas-acciones
// ---------------------------------------------------------------------------

interface UltimasAccionesFiltros {
  limite?: number
  actor_user_id?: string
  desde?: string
  hasta?: string
  materia_id?: string
}

/**
 * GET /api/v1/auditoria/ultimas-acciones
 * Returns the most recent audit events.
 */
export async function getUltimasAcciones(filtros?: UltimasAccionesFiltros): Promise<UltimaAccionItem[]> {
  try {
    const params = filtros
      ? toParams({
          limite: filtros.limite,
          actor_user_id: filtros.actor_user_id,
          desde: filtros.desde,
          hasta: filtros.hasta,
          materia_id: filtros.materia_id,
        })
      : undefined
    const response = await apiClient.get<UltimaAccionItem[]>('/auditoria/ultimas-acciones', { params })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
