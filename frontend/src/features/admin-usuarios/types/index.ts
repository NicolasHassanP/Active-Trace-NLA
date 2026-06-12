/**
 * Types for admin-usuarios feature — mirrors backend schemas (non-PII only).
 * No `any`. All unions are explicit literal types.
 * Fields aligned to:
 *   backend/app/schemas/usuario.py (UsuarioRead L138, UsuarioCreate L83, UsuarioUpdate L117)
 *   backend/app/models/usuario.py  (UsuarioEstado enum)
 *
 * CONTRATO OQ-3 (enforced here):
 *   NEVER include: dni, cuil, cbu, alias_cbu, banco, facturador, legajo_profesional,
 *   regional, auth_identity_id, tenant_id, email_hash.
 *   Those are PII financiera or auth internals — belong to C-24 / C-07 backend only.
 *
 * Endpoints: GET/POST/PATCH/DELETE /api/v1/admin/usuarios
 * Permission: usuarios:gestionar (all verbs) → ADMIN
 * Identity/tenant NEVER in the body — resolved from the JWT (rule #8/#9).
 */

/** Maps UsuarioEstado enum (backend/app/models/usuario.py). */
export type UsuarioEstado = 'activo' | 'inactivo'

// ---------------------------------------------------------------------------
// UsuarioRead — non-PII output shape
// ---------------------------------------------------------------------------

/** Resumen de una asignación dentro de UsuarioRead (non-PII). */
export interface AsignacionResumen {
  id: string
  rol: string
  materia_id: string | null
  carrera_id: string | null
  cohorte_id: string | null
  desde: string
  hasta: string | null
  estado_vigencia: string | null
}

/**
 * Mirrors UsuarioRead from backend/app/schemas/usuario.py (L138).
 * ONLY non-PII fields. NEVER dni/cuil/cbu/alias_cbu/tenant_id.
 */
export interface UsuarioRead {
  id: string
  email: string
  nombre: string
  apellidos: string
  legajo: string | null
  estado: UsuarioEstado
  asignaciones: AsignacionResumen[]
  created_at: string   // ISO datetime
  updated_at: string   // ISO datetime
}

// ---------------------------------------------------------------------------
// UsuarioCreate — non-PII create body
// ---------------------------------------------------------------------------

/**
 * POST /api/v1/admin/usuarios body — non-PII fields only.
 * tenant_id NEVER included — resolved from the JWT.
 * EXCLUDES: dni, cuil, cbu, alias_cbu, banco, facturador,
 *           legajo_profesional, regional, auth_identity_id.
 */
export interface UsuarioCreate {
  email: string
  nombre: string
  apellidos: string
  legajo?: string | null
  estado?: UsuarioEstado
}

// ---------------------------------------------------------------------------
// UsuarioUpdate — non-PII partial update body
// ---------------------------------------------------------------------------

/**
 * PATCH /api/v1/admin/usuarios/{id} body — all optional, non-PII only.
 * EXCLUDES PII financiera fields.
 */
export interface UsuarioUpdate {
  email?: string | null
  nombre?: string | null
  apellidos?: string | null
  legajo?: string | null
  estado?: UsuarioEstado | null
}

// ---------------------------------------------------------------------------
// Client-side filter state
// ---------------------------------------------------------------------------

/** Client-side filter for Usuarios table — in-memory. */
export interface UsuarioClientFiltros {
  nombre?: string
  email?: string
  estado?: UsuarioEstado | ''
}

/** Ordered list of UsuarioEstado values for selects. */
export const ESTADOS_USUARIO: UsuarioEstado[] = ['activo', 'inactivo']
