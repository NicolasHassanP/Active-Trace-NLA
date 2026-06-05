/**
 * comunicacionService — wraps Comunicaciones API endpoints.
 * Identity/tenant NEVER in request bodies — they travel via JWT (apiClient interceptor).
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type {
  PreviewRequest,
  PreviewResponse,
  EncolarRequest,
  EncolarResponse,
  LoteStatusResponse,
  ComunicacionRead,
} from '../types'

/** POST /comunicaciones/preview — renders the template for a sample destinatario */
export async function previewComunicacion(request: PreviewRequest): Promise<PreviewResponse> {
  try {
    const response = await apiClient.post<PreviewResponse>('/comunicaciones/preview', request)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/** POST /comunicaciones/encolar — queues a batch. Body has NO identity/tenant fields. */
export async function encolarLote(request: EncolarRequest): Promise<EncolarResponse> {
  try {
    const response = await apiClient.post<EncolarResponse>('/comunicaciones/encolar', request)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/** GET /comunicaciones/lote/{loteId} — returns the current status of a batch */
export async function getLote(loteId: string): Promise<LoteStatusResponse> {
  try {
    const response = await apiClient.get<LoteStatusResponse>(`/comunicaciones/lote/${loteId}`)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/** POST /comunicaciones/aprobar-lote — approves all pending messages in a batch */
export async function aprobarLote(loteId: string): Promise<ComunicacionRead[]> {
  try {
    const response = await apiClient.post<ComunicacionRead[]>('/comunicaciones/aprobar-lote', { lote_id: loteId })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/** POST /comunicaciones/cancelar-lote — cancels the batch (409 = invalid transition) */
export async function cancelarLote(loteId: string): Promise<ComunicacionRead[]> {
  try {
    const response = await apiClient.post<ComunicacionRead[]>('/comunicaciones/cancelar-lote', { lote_id: loteId })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/** POST /comunicaciones/aprobar-individual — approves a single message */
export async function aprobarIndividual(comunicacionId: string): Promise<ComunicacionRead> {
  try {
    const response = await apiClient.post<ComunicacionRead>('/comunicaciones/aprobar-individual', { comunicacion_id: comunicacionId })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/** POST /comunicaciones/cancelar-individual — cancels a single message (404 = message not found) */
export async function cancelarIndividual(comunicacionId: string): Promise<ComunicacionRead> {
  try {
    const response = await apiClient.post<ComunicacionRead>('/comunicaciones/cancelar-individual', { comunicacion_id: comunicacionId })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
