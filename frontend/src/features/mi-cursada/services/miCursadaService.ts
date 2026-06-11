/**
 * miCursadaService — wraps C-25 alumno-portal API endpoint.
 * Identity/tenant never in request body — they travel via JWT (apiClient interceptor).
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type { EstadoAcademicoRead } from '../types'

/** GET /api/v1/alumno/estado-academico — estado académico del alumno autenticado. */
export async function getEstadoAcademico(): Promise<EstadoAcademicoRead> {
  try {
    const response = await apiClient.get<EstadoAcademicoRead>('/alumno/estado-academico')
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
