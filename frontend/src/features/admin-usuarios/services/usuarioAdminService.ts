/**
 * usuarioAdminService — wraps the Usuarios ABM API endpoints.
 * All endpoints require ADMIN role (usuarios:gestionar).
 * Identity/tenant never in the request body — they travel via JWT (apiClient interceptor).
 * Errors are wrapped with parseDomainError for typed handling.
 *
 * CONTRATO OQ-3: body ONLY contains non-PII fields.
 * NEVER send: dni, cuil, cbu, alias_cbu, banco, facturador, legajo_profesional,
 *             regional, auth_identity_id, tenant_id.
 *
 * Endpoints:
 *   GET    /api/v1/admin/usuarios           — list usuarios (usuarios:gestionar)
 *   POST   /api/v1/admin/usuarios           — create (201 UsuarioRead)
 *   PATCH  /api/v1/admin/usuarios/{id}      — partial update (200 UsuarioRead)
 *   DELETE /api/v1/admin/usuarios/{id}      — soft delete (204)
 *
 * Domain exceptions mapped by backend:
 *   ConflictoEmail      → 409
 *   UsuarioNoEncontrado → 404
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type { UsuarioRead, UsuarioCreate, UsuarioUpdate } from '../types'

/**
 * GET /api/v1/admin/usuarios
 * Returns usuarios for the current tenant (tenant-scoped on the backend).
 */
export async function listarUsuarios(): Promise<UsuarioRead[]> {
  try {
    const response = await apiClient.get<UsuarioRead[]>('/admin/usuarios')
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * POST /api/v1/admin/usuarios
 * Creates a new usuario. Returns the created UsuarioRead on 201.
 * tenant_id resolved from the JWT — never in the body.
 * Only sends non-PII fields (OQ-3).
 */
export async function crearUsuario(body: UsuarioCreate): Promise<UsuarioRead> {
  try {
    const response = await apiClient.post<UsuarioRead>('/admin/usuarios', body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * PATCH /api/v1/admin/usuarios/{id}
 * Partial update of a usuario. Returns the updated UsuarioRead on 200.
 * Only sends non-PII fields (OQ-3).
 */
export async function editarUsuario(id: string, body: UsuarioUpdate): Promise<UsuarioRead> {
  try {
    const response = await apiClient.patch<UsuarioRead>(`/admin/usuarios/${id}`, body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * DELETE /api/v1/admin/usuarios/{id}
 * Soft delete (baja lógica). Returns undefined on 204.
 */
export async function darBajaUsuario(id: string): Promise<void> {
  try {
    await apiClient.delete(`/admin/usuarios/${id}`)
  } catch (err) {
    throw parseDomainError(err)
  }
}
