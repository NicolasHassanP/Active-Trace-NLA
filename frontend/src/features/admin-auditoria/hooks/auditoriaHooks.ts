/**
 * auditoriaHooks — TanStack Query hooks for admin-auditoria (read-only).
 * No mutations — panel is fully read-only.
 * Query keys include filtros so different filter combos are cached separately.
 *
 * Permission: auditoria:ver → ADMIN.
 */
import { useQuery } from '@tanstack/react-query'
import {
  listarEventos,
  getAccionesPorDia,
  getInteraccionesDocente,
  getInteraccionesDocenteMateria,
  getComunicacionesPorDocente,
  getUltimasAcciones,
} from '../services/auditoriaService'
import type { AuditoriaFiltros, MetricaFiltros } from '../types'

// ---------------------------------------------------------------------------
// Events list — paginated
// ---------------------------------------------------------------------------

/**
 * Query hook for GET /api/v1/auditoria.
 * filtros is included in the queryKey so different pages/filters are cached independently.
 */
export function useEventosAuditoria(filtros: AuditoriaFiltros) {
  return useQuery({
    queryKey: ['admin-auditoria', 'eventos', filtros] as const,
    queryFn: () => listarEventos(filtros),
  })
}

// ---------------------------------------------------------------------------
// Metrics hooks — no mutations
// ---------------------------------------------------------------------------

/** Query hook for GET /api/v1/auditoria/metricas/acciones-por-dia. */
export function useAccionesPorDia(filtros: MetricaFiltros) {
  return useQuery({
    queryKey: ['admin-auditoria', 'metricas', 'acciones-por-dia', filtros] as const,
    queryFn: () => getAccionesPorDia(filtros),
  })
}

/** Query hook for GET /api/v1/auditoria/metricas/interacciones-docente. */
export function useInteraccionesDocente(filtros: MetricaFiltros) {
  return useQuery({
    queryKey: ['admin-auditoria', 'metricas', 'interacciones-docente', filtros] as const,
    queryFn: () => getInteraccionesDocente(filtros),
  })
}

/** Query hook for GET /api/v1/auditoria/metricas/interacciones-docente-materia. */
export function useInteraccionesDocenteMateria(filtros: MetricaFiltros) {
  return useQuery({
    queryKey: ['admin-auditoria', 'metricas', 'interacciones-docente-materia', filtros] as const,
    queryFn: () => getInteraccionesDocenteMateria(filtros),
  })
}

/** Query hook for GET /api/v1/auditoria/metricas/comunicaciones-por-docente. */
export function useComunicacionesPorDocente(estado?: string) {
  return useQuery({
    queryKey: ['admin-auditoria', 'metricas', 'comunicaciones-por-docente', estado ?? null] as const,
    queryFn: () => getComunicacionesPorDocente(estado),
  })
}

// ---------------------------------------------------------------------------
// Ultimas acciones
// ---------------------------------------------------------------------------

/** Query hook for GET /api/v1/auditoria/ultimas-acciones. */
export function useUltimasAcciones(limite?: number) {
  return useQuery({
    queryKey: ['admin-auditoria', 'ultimas-acciones', limite ?? null] as const,
    queryFn: () => getUltimasAcciones(limite !== undefined ? { limite } : undefined),
  })
}
