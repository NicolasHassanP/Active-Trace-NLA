/**
 * atrasadosService — wraps Análisis API endpoints for student delay tracking.
 * Identity/tenant never in request body — they travel via JWT (apiClient interceptor).
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type { AlumnoAtrasado, ReporteMateria } from '../types'

interface ListarAtrasadosParams {
  materia_id: string
  cohorte_id: string
  actividades?: string[]
}

/**
 * GET /analisis/atrasados — returns students behind on activities.
 * Supports optional `actividades[]` filter.
 */
export async function listarAtrasados(params: ListarAtrasadosParams): Promise<AlumnoAtrasado[]> {
  try {
    const response = await apiClient.get<AlumnoAtrasado[]>('/analisis/atrasados', {
      params: {
        materia_id: params.materia_id,
        cohorte_id: params.cohorte_id,
        ...(params.actividades ? { actividades: params.actividades } : {}),
      },
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * GET /analisis/reporte-materia — returns aggregate metrics for a materia×cohorte.
 * Returns sin_datos=true when metrics are not yet computable.
 */
export async function reporteMateria(materia_id: string, cohorte_id: string): Promise<ReporteMateria> {
  try {
    const response = await apiClient.get<ReporteMateria>('/analisis/reporte-materia', {
      params: { materia_id, cohorte_id },
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
