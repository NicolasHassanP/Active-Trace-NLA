/**
 * inboxUsuariosService — buscador de usuarios para mensajería.
 * Endpoint: GET /api/v1/inbox/usuarios?q=
 * Gateado por: inbox:usar
 * Identidad/tenant nunca en la petición — viajan vía JWT (apiClient interceptor).
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type { UsuarioAsignable } from '@/features/asignaciones/types'

/**
 * GET /api/v1/inbox/usuarios?q=...
 * Busca usuarios del tenant para el combobox de destinatario en mensajería.
 * Retorna la misma forma UsuarioAsignable que el combobox ya consume.
 */
export async function buscarUsuariosInbox(q: string): Promise<UsuarioAsignable[]> {
  try {
    const response = await apiClient.get<UsuarioAsignable[]>('/inbox/usuarios', {
      params: q.trim() ? { q: q.trim() } : undefined,
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
