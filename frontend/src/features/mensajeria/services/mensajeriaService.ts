/**
 * mensajeriaService — wraps C-20 Inbox API endpoints.
 * Identity/tenant never in request body — they travel via JWT (apiClient interceptor).
 */
import { z } from 'zod'
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type { HiloCreate, InboxHiloRead, MensajeRead, RespuestaCreate } from '../types'

// ---------------------------------------------------------------------------
// Task 2.5 — Zod schemas
// ---------------------------------------------------------------------------

export const nuevoHiloSchema = z.object({
  destinatario_id: z.string().uuid('UUID de destinatario inválido'),
  asunto: z.string().optional(),
  cuerpo: z.string().min(1, 'El cuerpo no puede estar vacío'),
})

export type NuevoHiloValues = z.infer<typeof nuevoHiloSchema>

export const responderSchema = z.object({
  asunto: z.string().min(1, 'El asunto no puede estar vacío'),
  cuerpo: z.string().min(1, 'El cuerpo no puede estar vacío'),
})

export type ResponderValues = z.infer<typeof responderSchema>

// ---------------------------------------------------------------------------
// Task 2.1 — listarHilos
// ---------------------------------------------------------------------------

/** GET /api/v1/inbox — hilos del usuario autenticado con conteo de no leídos. */
export async function listarHilos(): Promise<InboxHiloRead[]> {
  try {
    const response = await apiClient.get<InboxHiloRead[]>('/inbox')
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Task 2.2 — abrirHilo
// ---------------------------------------------------------------------------

/** GET /api/v1/inbox/{hilo_id} — mensajes del hilo en orden; marca leído. */
export async function abrirHilo(hiloId: string): Promise<MensajeRead[]> {
  try {
    const response = await apiClient.get<MensajeRead[]>(`/inbox/${hiloId}`)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Task 2.3 — iniciarHilo
// ---------------------------------------------------------------------------

/** POST /api/v1/inbox — inicia un hilo 1:1. Identidad/tenant nunca en el body. */
export async function iniciarHilo(body: HiloCreate): Promise<MensajeRead> {
  try {
    const response = await apiClient.post<MensajeRead>('/inbox', body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Task 2.4 — responder
// ---------------------------------------------------------------------------

/** POST /api/v1/inbox/{hilo_id}/responder — agrega mensaje al hilo. */
export async function responder(hiloId: string, body: RespuestaCreate): Promise<MensajeRead> {
  try {
    const response = await apiClient.post<MensajeRead>(`/inbox/${hiloId}/responder`, body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
