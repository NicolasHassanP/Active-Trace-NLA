/**
 * Wire types for Perfil feature — mirrors the backend PerfilRead / PerfilUpdate schemas.
 * No `any`. Identity (id, cuil, legajo) is read-only and NEVER sent in the PATCH body.
 * The backend resolves the user from the JWT — the front never sends usuario_id/id.
 */

/**
 * Response of GET /api/v1/perfil and PATCH /api/v1/perfil — mirrors PerfilRead.
 * Read-only fields: id, cuil, legajo (shown disabled, never patched).
 */
export interface PerfilRead {
  id: string                       // uuid — RO
  email: string
  nombre: string
  apellidos: string
  dni: string | null
  cuil: string | null              // RO
  cbu: string | null
  alias_cbu: string | null
  genero: string | null
  legajo: string | null            // RO
  legajo_profesional: string | null
  banco: string | null
  regional: string | null
  facturador: boolean
  created_at: string               // ISO datetime
  updated_at: string               // ISO datetime
}

/**
 * Body of PATCH /api/v1/perfil — mirrors PerfilUpdate.
 * Only the 11 EDITABLE fields. Partial PATCH: every field optional.
 * `id`, `cuil`, `legajo`, `created_at`, `updated_at` are NEVER part of this body
 * (backend uses extra='forbid' → 422 on any undeclared field).
 */
export interface PerfilUpdate {
  nombre?: string
  apellidos?: string
  dni?: string | null
  genero?: string | null
  banco?: string | null
  cbu?: string | null
  alias_cbu?: string | null
  regional?: string | null
  email?: string
  facturador?: boolean
  legajo_profesional?: string | null
}
