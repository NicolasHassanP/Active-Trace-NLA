/**
 * Types for admin-auditoria feature — mirrors backend schemas exactly.
 * No `any`. All unions are explicit literal types.
 * Fields aligned to:
 *   backend/app/schemas/audit.py (AuditEventRead)
 *   backend/app/schemas/auditoria_metricas.py (metrics + UltimaAccionItem)
 *   backend/app/models/audit.py (AuditAction, AuditResultado)
 *   backend/app/models/comunicacion.py (ComunicacionEstado)
 *
 * Endpoints: GET /api/v1/auditoria (paginated), /metricas/*, /ultimas-acciones
 * Permission: auditoria:ver → ADMIN
 */

// ---------------------------------------------------------------------------
// Enums (mirrors Python models)
// ---------------------------------------------------------------------------

/**
 * Maps AuditAction (backend/app/models/audit.py).
 * Exhaustive — update if new actions are added.
 */
export type AuditAction = string  // Kept flexible — backend may add new actions

/** Maps AuditResultado (backend/app/models/audit.py). */
export type AuditResultado = 'ok' | 'error' | 'forbidden'

/** Maps ComunicacionEstado (backend/app/models/comunicacion.py). */
export type ComunicacionEstado = string  // Kept flexible

// ---------------------------------------------------------------------------
// AuditEventRead — main event schema
// ---------------------------------------------------------------------------

/** Mirrors AuditEventRead from backend/app/schemas/audit.py. */
export interface AuditEventRead {
  id: string                         // UUID
  tenant_id: string                  // UUID
  actor_user_id: string              // UUID (= auth_identity.id, JWT sub)
  impersonated_user_id: string | null  // UUID or null
  accion: AuditAction
  modulo: string
  entidad_tipo: string
  entidad_id: string | null
  resultado: AuditResultado
  registros_afectados: number | null
  ip: string | null
  user_agent: string | null
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  created_at: string                 // ISO datetime
  /** Resolved display name for actor_user_id. Null for orphan auth identities. */
  actor_nombre?: string | null
  /** Resolved entity name for Materia/Carrera/Cohorte. Null for other types. */
  entidad_nombre?: string | null
}

// ---------------------------------------------------------------------------
// Metric item types
// ---------------------------------------------------------------------------

/** Mirrors AccionesPorDiaItem. */
export interface AccionesPorDiaItem {
  dia: string    // ISO datetime (date_trunc day)
  total: number
}

/** Mirrors AccionesPorDiaResponse. */
export interface AccionesPorDiaResponse {
  items: AccionesPorDiaItem[]
}

/** Mirrors InteraccionesDocenteItem. */
export interface InteraccionesDocenteItem {
  actor_user_id: string   // UUID
  accion: AuditAction
  total: number
  /** Resolved display name for actor_user_id. */
  actor_nombre?: string | null
}

/** Mirrors InteraccionesDocenteResponse. */
export interface InteraccionesDocenteResponse {
  items: InteraccionesDocenteItem[]
}

/** Mirrors InteraccionesDocenteMateriaItem. */
export interface InteraccionesDocenteMateriaItem {
  actor_user_id: string   // UUID
  materia_id: string | null
  total: number
  /** Resolved display name for actor_user_id. */
  actor_nombre?: string | null
  /** Resolved display name for materia_id. */
  materia_nombre?: string | null
}

/** Mirrors InteraccionesDocenteMateriaResponse. */
export interface InteraccionesDocenteMateriaResponse {
  items: InteraccionesDocenteMateriaItem[]
}

/** Mirrors ComunicacionesPorDocenteItem. */
export interface ComunicacionesPorDocenteItem {
  enviado_por: string | null  // UUID or null
  estado: ComunicacionEstado
  total: number
}

/** Mirrors ComunicacionesPorDocenteResponse. */
export interface ComunicacionesPorDocenteResponse {
  items: ComunicacionesPorDocenteItem[]
}

/**
 * Mirrors UltimaAccionItem — same shape as AuditEventRead (C-05).
 */
export type UltimaAccionItem = AuditEventRead

// ---------------------------------------------------------------------------
// Filtros for the events list
// ---------------------------------------------------------------------------

/** Query params for GET /api/v1/auditoria — offset pagination. */
export interface AuditoriaFiltros {
  limit?: number
  offset?: number
  desde?: string   // ISO date string
  hasta?: string   // ISO date string
  /** Client-side text filter on actor_nombre (not sent to API). */
  actor_nombre_q?: string
}

/** Query params for the metrics that accept date range + actor filters. */
export interface MetricaFiltros {
  desde?: string
  hasta?: string
  actor_user_id?: string
  materia_id?: string
}
