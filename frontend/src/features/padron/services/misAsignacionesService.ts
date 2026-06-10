import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'

export interface MiAsignacionRead {
  materia_id: string | null
  materia_nombre: string | null
  cohorte_id: string | null
  cohorte_nombre: string | null
  rol: string
  comisiones: string[]
}

export async function getMisAsignaciones(): Promise<MiAsignacionRead[]> {
  try {
    const response = await apiClient.get<MiAsignacionRead[]>('/perfil/mis-asignaciones')
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
