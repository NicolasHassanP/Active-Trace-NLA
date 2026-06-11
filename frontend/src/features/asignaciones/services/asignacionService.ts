/**
 * asignacionService — wraps the Asignaciones API endpoints.
 * All endpoints require the 'equipos:asignar' permission (COORDINADOR, ADMIN).
 * Identity/tenant never in the request body — they travel via JWT (apiClient interceptor).
 * Errors are wrapped with parseDomainError for typed handling.
 *
 * Endpoints:
 *   GET    /api/v1/asignaciones            — list with optional filters
 *   POST   /api/v1/asignaciones            — create
 *   PATCH  /api/v1/asignaciones/{id}       — partial update
 *   DELETE /api/v1/asignaciones/{id}       — soft delete (204)
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type {
  AsignacionRead,
  AsignacionCreate,
  AsignacionUpdate,
  AsignacionFiltros,
  UsuarioAsignable,
} from '../types'

/** Builds query params from filtros, omitting null/undefined values. */
function filtrosToParams(filtros: AsignacionFiltros): Record<string, string> {
  const params: Record<string, string> = {}
  if (filtros.usuario_id != null) params['usuario_id'] = filtros.usuario_id
  if (filtros.rol != null) params['rol'] = filtros.rol
  if (filtros.responsable_id != null) params['responsable_id'] = filtros.responsable_id
  return params
}

/**
 * GET /api/v1/asignaciones
 * Returns asignaciones filtered by the provided filtros (tenant-scoped on the backend).
 */
export async function listarAsignaciones(
  filtros: AsignacionFiltros,
): Promise<AsignacionRead[]> {
  try {
    const response = await apiClient.get<AsignacionRead[]>('/asignaciones', {
      params: filtrosToParams(filtros),
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * POST /api/v1/asignaciones
 * Creates a new asignacion. Returns the created AsignacionRead on 201.
 * tenant_id resolved from the JWT — never in the body.
 */
export async function crearAsignacion(body: AsignacionCreate): Promise<AsignacionRead> {
  try {
    const response = await apiClient.post<AsignacionRead>('/asignaciones', body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * PATCH /api/v1/asignaciones/{id}
 * Partial update of an asignacion. Returns the updated AsignacionRead on 200.
 */
export async function editarAsignacion(
  id: string,
  body: AsignacionUpdate,
): Promise<AsignacionRead> {
  try {
    const response = await apiClient.patch<AsignacionRead>(`/asignaciones/${id}`, body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * DELETE /api/v1/asignaciones/{id}
 * Soft delete (baja lógica). Returns undefined on 204.
 */
export async function darBajaAsignacion(id: string): Promise<void> {
  try {
    await apiClient.delete(`/asignaciones/${id}`)
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * GET /api/v1/asignaciones/usuarios?q=...
 * Busca usuarios asignables (no-PII) para el combobox de asignaciones.
 * Requiere permiso equipos:asignar (COORDINADOR, ADMIN).
 * Tenant-scoped en el backend — nunca se envía tenant_id en la petición.
 */
export async function buscarUsuariosAsignables(q: string): Promise<UsuarioAsignable[]> {
  try {
    const response = await apiClient.get<UsuarioAsignable[]>('/asignaciones/usuarios', {
      params: q.trim() ? { q: q.trim() } : undefined,
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
