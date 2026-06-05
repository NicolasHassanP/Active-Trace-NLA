/**
 * Atrasados TanStack Query hooks.
 * queryKey includes all active filters to ensure correct cache invalidation (OQ-1).
 */
import { useQuery } from '@tanstack/react-query'
import { listarAtrasados, reporteMateria } from '../services/atrasadosService'

interface UseAtrasadosParams {
  materia_id: string
  cohorte_id: string
  actividades?: string[]
}

/**
 * Query hook for GET /analisis/atrasados.
 * queryKey: ['atrasados', materiaId, cohorteId, actividades] — full filter set for correct cache.
 */
export function useAtrasados(params: UseAtrasadosParams) {
  return useQuery({
    queryKey: ['atrasados', params.materia_id, params.cohorte_id, params.actividades ?? []],
    queryFn: () => listarAtrasados(params),
    enabled: Boolean(params.materia_id && params.cohorte_id),
  })
}

/**
 * Query hook for GET /analisis/reporte-materia.
 * queryKey: ['reporte-materia', materiaId, cohorteId]
 */
export function useReporteMateria(materia_id: string, cohorte_id: string) {
  return useQuery({
    queryKey: ['reporte-materia', materia_id, cohorte_id],
    queryFn: () => reporteMateria(materia_id, cohorte_id),
    enabled: Boolean(materia_id && cohorte_id),
  })
}
