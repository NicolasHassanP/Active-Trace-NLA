/**
 * Wire types for Tareas feature — mirrors C-16 backend schemas (snake_case).
 * No `any`. All unions are explicit literal types.
 * Fields aligned to backend/app/schemas/tarea.py and backend/app/models/tarea.py.
 * Task 3.1.
 */

// ---------------------------------------------------------------------------
// Enums / literal unions
// ---------------------------------------------------------------------------

/**
 * TareaEstado — workflow state machine (mirrors TareaEstado enum in backend).
 * Transitions: Pendiente → {EnProgreso, Resuelta, Cancelada}
 *              EnProgreso → {Pendiente, Resuelta, Cancelada}
 *              Resuelta   → {EnProgreso}  (reopen)
 *              Cancelada  → {}            (terminal)
 */
export type TareaEstado = 'Pendiente' | 'EnProgreso' | 'Resuelta' | 'Cancelada'

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

/** Mirrors TareaRead from backend/app/schemas/tarea.py */
export interface TareaRead {
  id: string
  tenant_id: string
  asignado_a: string
  asignado_por: string
  descripcion: string
  estado: TareaEstado
  materia_id: string | null
  contexto_id: string | null
  contexto_tipo: string | null
  created_at: string        // ISO datetime string
  updated_at: string        // ISO datetime string
  deleted_at: string | null
  // Enriched fields resolved by JOIN in the repository (D12).
  // Always present in API responses (null when not resolvable).
  materia_nombre?: string | null
  asignado_por_nombre?: string | null
  asignado_a_nombre?: string | null
}

/** Mirrors ComentarioTareaRead from backend/app/schemas/tarea.py */
export interface ComentarioTareaRead {
  id: string
  tenant_id: string
  tarea_id: string
  autor_id: string
  cuerpo: string
  es_sistema: boolean
  created_at: string        // ISO datetime string
  updated_at: string        // ISO datetime string
  deleted_at: string | null
}

// ---------------------------------------------------------------------------
// Request types
// ---------------------------------------------------------------------------

/**
 * POST /api/v1/tareas — mirrors TareaCreate.
 * tenant_id, asignado_por, autor_id NEVER included — from JWT.
 * contexto_id + contexto_tipo: both null or both present.
 */
export interface TareaCreateRequest {
  asignado_a: string
  descripcion: string
  materia_id?: string | null
  contexto_id?: string | null
  contexto_tipo?: string | null
}

/** PATCH /api/v1/tareas/{id}/estado — mirrors TareaUpdateEstado */
export interface TareaUpdateEstadoRequest {
  estado: TareaEstado
}

/** POST /api/v1/tareas/{id}/delegar — mirrors TareaDelegar */
export interface TareaDelegarRequest {
  asignado_a: string
}

/** POST /api/v1/tareas/{id}/comentarios — mirrors ComentarioTareaCreate */
export interface ComentarioTareaCreateRequest {
  cuerpo: string
}

// ---------------------------------------------------------------------------
// Query / filter types
// ---------------------------------------------------------------------------

/** Query params for GET /api/v1/tareas/admin */
export interface TareasAdminParams {
  asignado_a?: string | null
  asignado_por?: string | null
  materia_id?: string | null
  estado?: TareaEstado | null
  q?: string | null
}
