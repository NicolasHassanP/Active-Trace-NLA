/**
 * equiposService — wraps C-08 Equipos API endpoints.
 * Identity/tenant never in request body — they travel via JWT (apiClient interceptor).
 * Errors are wrapped with parseDomainError for typed handling.
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type {
  MisEquiposItem,
  AsignacionMasivaRequest,
  ClonarEquipoRequest,
  EquipoQueryParams,
  ResumenClonacion,
  ResumenLote,
  VigenciaGeneralRequest,
  VigenciaGeneralResponse,
} from '../types'

/**
 * GET /api/v1/equipos/mis-equipos
 * Returns the authenticated user's assignments with estado_vigencia.
 */
export async function listarMisEquipos(): Promise<MisEquiposItem[]> {
  try {
    const response = await apiClient.get<MisEquiposItem[]>('/equipos/mis-equipos')
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * GET /api/v1/equipos
 * Queries the docente team for a tripleta (materia × carrera × cohorte).
 * Supports optional filters: rol, responsable_id.
 */
export async function consultarEquipo(params: EquipoQueryParams): Promise<MisEquiposItem[]> {
  try {
    const response = await apiClient.get<MisEquiposItem[]>('/equipos', {
      params: {
        materia_id: params.materia_id,
        carrera_id: params.carrera_id,
        cohorte_id: params.cohorte_id,
        ...(params.rol != null ? { rol: params.rol } : {}),
        ...(params.responsable_id != null ? { responsable_id: params.responsable_id } : {}),
      },
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * POST /api/v1/equipos/asignacion-masiva
 * Creates N assignments atomically. Returns ResumenLote on 201.
 * Throws DomainError with status 422 on invalid reference.
 */
export async function asignacionMasiva(body: AsignacionMasivaRequest): Promise<ResumenLote> {
  try {
    const response = await apiClient.post<ResumenLote>('/equipos/asignacion-masiva', body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * POST /api/v1/equipos/clonar
 * Non-destructive clone from origen tripleta to destino tripleta.
 * Duplicates are skipped (omitidas). Returns ResumenClonacion on 201.
 */
export async function clonarEquipo(body: ClonarEquipoRequest): Promise<ResumenClonacion> {
  try {
    const response = await apiClient.post<ResumenClonacion>('/equipos/clonar', body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * PATCH /api/v1/equipos/vigencia-general
 * Updates desde/hasta for all active assignments of the tripleta.
 * Returns { afectadas: N } on 200.
 */
export async function vigenciaGeneral(body: VigenciaGeneralRequest): Promise<VigenciaGeneralResponse> {
  try {
    const response = await apiClient.patch<VigenciaGeneralResponse>('/equipos/vigencia-general', body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * GET /api/v1/equipos/exportar
 * Returns a CSV Blob attachment for the queried equipo.
 * Caller uses downloadFile() to trigger the browser download.
 */
export async function exportarEquipo(params: EquipoQueryParams): Promise<Blob> {
  try {
    const response = await apiClient.get<Blob>('/equipos/exportar', {
      responseType: 'blob',
      params: {
        materia_id: params.materia_id,
        carrera_id: params.carrera_id,
        cohorte_id: params.cohorte_id,
        ...(params.rol != null ? { rol: params.rol } : {}),
        ...(params.responsable_id != null ? { responsable_id: params.responsable_id } : {}),
      },
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
