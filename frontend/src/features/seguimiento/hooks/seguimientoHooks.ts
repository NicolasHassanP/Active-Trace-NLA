/**
 * Seguimiento TanStack Query hooks.
 * queryKey includes ALL active filter params for correct cache invalidation.
 * Different filter combinations produce independent cache entries.
 */
import { useQuery } from '@tanstack/react-query'
import { listarSeguimiento } from '../services/seguimientoService'
import type { SeguimientoParams } from '../types'

/**
 * Stable queryKey factory — ALL filter fields included.
 */
function seguimientoKey(params: SeguimientoParams) {
  return [
    'seguimiento',
    params.materia_id ?? null,
    params.cohorte_id ?? null,
    params.busqueda ?? null,
    params.comision ?? null,
    params.regional ?? null,
    params.min_cumplidas ?? null,
  ] as const
}

/**
 * Query hook for GET /api/v1/analisis/monitor (seguimiento scope).
 */
export function useSeguimiento(params: SeguimientoParams) {
  return useQuery({
    queryKey: seguimientoKey(params),
    queryFn: () => listarSeguimiento(params),
    enabled: !!(params.materia_id && params.cohorte_id),
  })
}
