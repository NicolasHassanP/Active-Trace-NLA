/**
 * misColoquiosService — HU-47 ALUMNO: convocatorias, reservar, cancelar.
 * Identity/tenant never in request body — they travel via JWT (apiClient interceptor).
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type { ConvocatoriasAlumnoRead, ReservaRead, ReservaRequest } from '../types'

/** GET /api/v1/coloquios/mis-convocatorias — convocatorias donde el alumno es candidato. */
export async function getMisConvocatorias(): Promise<ConvocatoriasAlumnoRead[]> {
  try {
    const response = await apiClient.get<ConvocatoriasAlumnoRead[]>('/coloquios/mis-convocatorias')
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/** POST /api/v1/coloquios/reservas — reservar un turno. */
export async function reservarTurno(payload: ReservaRequest): Promise<ReservaRead> {
  try {
    const response = await apiClient.post<ReservaRead>('/coloquios/reservas', payload)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/** DELETE /api/v1/coloquios/reservas/{reservaId} — cancelar la propia reserva. */
export async function cancelarReserva(reservaId: string): Promise<ReservaRead> {
  try {
    const response = await apiClient.delete<ReservaRead>(`/coloquios/reservas/${reservaId}`)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
