/**
 * padronService — wraps Padrón API endpoints.
 * Identity/tenant are NEVER included in request bodies — they travel via JWT (apiClient interceptor).
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type { ActivarRequest, PadronRowDTO, SyncMoodleRequest, VersionPadronRead } from '../types'

/**
 * POST /padron/preview — uploads file as multipart FormData.
 * Returns detected rows or throws DomainError on 422.
 */
export async function previewPadron(file: File): Promise<PadronRowDTO[]> {
  const form = new FormData()
  form.append('file', file)
  try {
    const response = await apiClient.post<PadronRowDTO[]>('/padron/preview', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * POST /padron/activar — confirms import with the previewed rows.
 * Body contains ONLY materia_id, cohorte_id, rows — no identity or tenant.
 * Returns VersionPadronRead on 201.
 */
export async function activarPadron(request: ActivarRequest): Promise<VersionPadronRead> {
  try {
    const response = await apiClient.post<VersionPadronRead>('/padron/activar', request)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * DELETE /padron/vaciar?materia_id=&cohorte_id= — empties the active padron.
 * Returns void on 204; throws DomainError on 404/403.
 */
export async function vaciarPadron(materia_id: string, cohorte_id: string): Promise<void> {
  try {
    await apiClient.delete('/padron/vaciar', { params: { materia_id, cohorte_id } })
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * POST /padron/sync-moodle — triggers on-demand sync from Moodle.
 * 201 → VersionPadronRead; 503 → Moodle not configured; 502 → Moodle unavailable.
 */
export async function syncMoodlePadron(request: SyncMoodleRequest): Promise<VersionPadronRead> {
  try {
    const response = await apiClient.post<VersionPadronRead>('/padron/sync-moodle', request)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
