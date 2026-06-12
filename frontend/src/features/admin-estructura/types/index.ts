/**
 * Types for admin-estructura feature — mirrors backend schemas exactly.
 * No `any`. All unions are explicit literal types.
 * Fields aligned to:
 *   backend/app/schemas/estructura.py
 *   backend/app/models/estructura.py (EstadoEstructura)
 *
 * Endpoints: GET/POST/PATCH/DELETE /api/v1/admin/{carreras,materias,cohortes}
 * Permission: estructura:ver (GET), estructura:gestionar (POST/PATCH/DELETE) → ADMIN
 * Identity/tenant NEVER in the body — resolved from the JWT (rule #8/#9).
 */

/** Maps EstadoEstructura enum (backend/app/models/estructura.py). */
export type EstadoEstructura = 'activa' | 'inactiva'

// ---------------------------------------------------------------------------
// Carrera
// ---------------------------------------------------------------------------

/** Mirrors CarreraRead from backend/app/schemas/estructura.py. */
export interface CarreraRead {
  id: string
  codigo: string
  nombre: string
  estado: EstadoEstructura
  created_at: string  // ISO datetime
  updated_at: string  // ISO datetime
}

/**
 * POST /api/v1/admin/carreras body — mirrors CarreraCreate.
 * tenant_id NEVER included — resolved from the JWT.
 */
export interface CarreraCreate {
  codigo: string
  nombre: string
}

/**
 * PATCH /api/v1/admin/carreras/{id} body — mirrors CarreraUpdate (all optional).
 */
export interface CarreraUpdate {
  codigo?: string | null
  nombre?: string | null
  estado?: EstadoEstructura | null
}

// ---------------------------------------------------------------------------
// Materia
// ---------------------------------------------------------------------------

/** Mirrors MateriaRead from backend/app/schemas/estructura.py. */
export interface MateriaRead {
  id: string
  codigo: string
  nombre: string
  estado: EstadoEstructura
  created_at: string
  updated_at: string
}

/**
 * POST /api/v1/admin/materias body — mirrors MateriaCreate.
 */
export interface MateriaCreate {
  codigo: string
  nombre: string
}

/**
 * PATCH /api/v1/admin/materias/{id} body — mirrors MateriaUpdate (all optional).
 */
export interface MateriaUpdate {
  codigo?: string | null
  nombre?: string | null
  estado?: EstadoEstructura | null
}

// ---------------------------------------------------------------------------
// Cohorte
// ---------------------------------------------------------------------------

/** Mirrors CohorteRead from backend/app/schemas/estructura.py. */
export interface CohorteRead {
  id: string
  carrera_id: string
  nombre: string
  anio: number
  vig_desde: string   // ISO date string (YYYY-MM-DD)
  vig_hasta: string | null  // ISO date string or null (cohorte abierta)
  estado: EstadoEstructura
  created_at: string
  updated_at: string
}

/**
 * POST /api/v1/admin/cohortes body — mirrors CohorteCreate.
 * carrera_id obligatorio, vig_hasta nullable = cohorte abierta.
 */
export interface CohorteCreate {
  carrera_id: string
  nombre: string
  anio: number
  vig_desde: string
  vig_hasta?: string | null
}

/**
 * PATCH /api/v1/admin/cohortes/{id} body — mirrors CohorteUpdate (all optional).
 */
export interface CohorteUpdate {
  nombre?: string | null
  anio?: number | null
  vig_desde?: string | null
  vig_hasta?: string | null
  estado?: EstadoEstructura | null
}

// ---------------------------------------------------------------------------
// Client-side filter state (carreras, materias, cohortes)
// ---------------------------------------------------------------------------

/** Client-side filter for Carreras table — in-memory. */
export interface CarreraClientFiltros {
  nombre?: string
  estado?: EstadoEstructura | ''
}

/** Client-side filter for Materias table — in-memory. */
export interface MateriaClientFiltros {
  nombre?: string
  estado?: EstadoEstructura | ''
}

/** Client-side filter for Cohortes table — in-memory. */
export interface CohorteClientFiltros {
  nombre?: string
  carrera_id?: string | ''
  estado?: EstadoEstructura | ''
}

/** Ordered list of EstadoEstructura values for selects. */
export const ESTADOS_ESTRUCTURA: EstadoEstructura[] = ['activa', 'inactiva']
