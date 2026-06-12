/**
 * Wire types for Asignaciones feature — mirrors backend schemas exactly.
 * No `any`. All unions are explicit literal types.
 * Fields aligned to:
 *   backend/app/models/usuario.py (RolAsignacion)
 *   backend/app/models/vigencia.py (EstadoVigencia)
 *   backend/app/schemas/usuario.py (AsignacionCreate, AsignacionUpdate, AsignacionRead)
 *
 * Endpoints: GET/POST/PATCH/DELETE /api/v1/asignaciones
 * Permission: equipos:asignar → COORDINADOR, ADMIN
 */

/** Maps RolAsignacion enum (backend/app/models/usuario.py). */
export type RolAsignacion =
  | 'PROFESOR'
  | 'TUTOR'
  | 'COORDINADOR'
  | 'NEXO'
  | 'ADMIN'
  | 'FINANZAS'

/** Maps EstadoVigencia enum (backend/app/models/vigencia.py). */
export type EstadoVigencia = 'vigente' | 'vencida' | 'no_iniciada'

/** Mirrors AsignacionRead from backend/app/schemas/usuario.py. */
export interface AsignacionRead {
  id: string
  usuario_id: string
  usuario_nombre?: string | null
  usuario_apellidos?: string | null
  rol: RolAsignacion
  desde: string             // ISO date string
  hasta: string | null      // ISO date string or null (open-ended)
  materia_id: string | null
  materia_nombre?: string | null
  carrera_id: string | null
  cohorte_id: string | null
  cohorte_nombre?: string | null
  comisiones: string[]
  responsable_id: string | null
  estado_vigencia: EstadoVigencia
  created_at: string        // ISO datetime
  updated_at: string        // ISO datetime
}

/**
 * POST /api/v1/asignaciones body — mirrors AsignacionCreate.
 * tenant_id NEVER included — resolved from the JWT on the backend.
 */
export interface AsignacionCreate {
  usuario_id: string
  rol: RolAsignacion
  desde: string             // ISO date string
  hasta?: string | null
  materia_id?: string | null
  carrera_id?: string | null
  cohorte_id?: string | null
  comisiones?: string[]
  responsable_id?: string | null
}

/**
 * PATCH /api/v1/asignaciones/{id} body — mirrors AsignacionUpdate (all optional).
 */
export interface AsignacionUpdate {
  rol?: RolAsignacion
  desde?: string
  hasta?: string | null
  materia_id?: string | null
  carrera_id?: string | null
  cohorte_id?: string | null
  comisiones?: string[]
  responsable_id?: string | null
}

/**
 * Query params for GET /api/v1/asignaciones — all optional.
 * These are the server-side params sent to the API.
 */
export interface AsignacionFiltros {
  usuario_id?: string | null
  rol?: RolAsignacion | null
  responsable_id?: string | null
}

/**
 * Client-side filter state for the Asignaciones table.
 * All filtering is done in-memory over the full list from the API.
 */
export interface AsignacionClientFiltros {
  usuario?: string        // substring match on "{nombre} {apellidos}"
  rol?: RolAsignacion | '' // exact match; '' means no filter
  materia?: string        // exact match on materia_nombre; '' means no filter
  cohorte?: string        // exact match on cohorte_nombre; '' means no filter
  vigencia?: EstadoVigencia | '' // exact match; '' means no filter
  desde?: string          // ISO date — keep rows with desde >= value
  hasta?: string          // ISO date — keep rows with desde <= value
}

/**
 * UsuarioAsignable — mirrors UsuarioAsignableRead from backend.
 * Returned by GET /api/v1/asignaciones/usuarios.
 * Only non-PII fields: id, nombre, apellidos, email, legajo.
 * NEVER includes dni, cuil, cbu, tenant_id.
 */
export interface UsuarioAsignable {
  id: string
  nombre: string
  apellidos: string
  email: string
  legajo?: string | null
}

/** Ordered list of RolAsignacion values for selects. */
export const ROLES_ASIGNACION: RolAsignacion[] = [
  'PROFESOR',
  'TUTOR',
  'COORDINADOR',
  'NEXO',
  'ADMIN',
  'FINANZAS',
]

/** Ordered list of EstadoVigencia values for selects. */
export const ESTADOS_VIGENCIA: EstadoVigencia[] = ['vigente', 'vencida', 'no_iniciada']
