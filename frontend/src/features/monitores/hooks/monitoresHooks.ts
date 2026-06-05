/**
 * Monitores TanStack Query hooks.
 * queryKey MUST include ALL active filter params for correct cache invalidation.
 * Task 4.4.
 */
import { useQuery } from '@tanstack/react-query'
import { listarMonitor } from '../services/monitoresService'
import type { MonitorParams } from '../types'

/**
 * Stable queryKey factory for the monitor query.
 * ALL filter fields are included so that different filter combinations
 * produce independent cache entries.
 */
function monitorKey(params: MonitorParams) {
  return [
    'monitor',
    params.materia_id ?? null,
    params.cohorte_id ?? null,
    params.comision ?? null,
    params.regional ?? null,
    params.busqueda ?? null,
    params.actividad ?? null,
    params.min_cumplidas ?? null,
    params.fecha_desde ?? null,
    params.fecha_hasta ?? null,
    params.actividades ?? null,
  ] as const
}

/**
 * Query hook for GET /api/v1/analisis/monitor.
 * queryKey includes ALL active filters — different filter combinations never
 * share cache entries (requirement from task 4.4 and spec).
 */
export function useMonitor(params: MonitorParams) {
  return useQuery({
    queryKey: monitorKey(params),
    queryFn: () => listarMonitor(params),
  })
}
