/**
 * Wire types for Equipos feature — mirrors C-08 backend schemas (snake_case).
 * No `any`. All unions are explicit literal types.
 * Fields aligned to backend/app/schemas/equipo.py.
 */

/** Rol de asignación docente — mirrors app.models.usuario.RolAsignacion */
export type RolAsignacion =
  | 'PROFESOR'
  | 'TUTOR'
  | 'COORDINADOR'
  | 'NEXO'

/** Estado de vigencia derivado — mirrors app.models.vigencia.EstadoVigencia */
export type EstadoVigencia = 'vigente' | 'vencida' | 'futura'

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

/** Ítem de GET /api/v1/equipos/mis-equipos — mirrors MisEquiposItem */
export interface MisEquiposItem {
  asignacion_id: string
  materia_id: string | null
  carrera_id: string | null
  cohorte_id: string | null
  rol: RolAsignacion
  desde: string          // ISO date string
  hasta: string | null   // ISO date string or null (open-ended)
  estado_vigencia: EstadoVigencia
  comisiones: string[]
  responsable_id: string | null
}

/** Respuesta de POST /api/v1/equipos/asignacion-masiva — mirrors ResumenLote */
export interface ResumenLote {
  creadas: number
}

/** Respuesta de POST /api/v1/equipos/clonar — mirrors ResumenClonacion */
export interface ResumenClonacion {
  clonadas: number
  omitidas: number
}

/** Respuesta de PATCH /api/v1/equipos/vigencia-general */
export interface VigenciaGeneralResponse {
  afectadas: number
}

// ---------------------------------------------------------------------------
// Request types
// ---------------------------------------------------------------------------

/**
 * POST /api/v1/equipos/asignacion-masiva — mirrors AsignacionMasivaRequest.
 * usuario_ids: non-empty array of UUIDs (validated by Zod on the client).
 * tenant_id NEVER included — comes from JWT.
 */
export interface AsignacionMasivaRequest {
  usuario_ids: string[]
  materia_id: string
  carrera_id: string
  cohorte_id: string
  rol: RolAsignacion
  desde: string          // ISO date string
  hasta?: string | null
  comisiones?: string[]
  responsable_id?: string | null
}

/**
 * POST /api/v1/equipos/clonar — mirrors ClonarEquipoRequest.
 * Non-destructive: duplicates are skipped (omitidas).
 */
export interface ClonarEquipoRequest {
  origen_materia_id: string
  origen_carrera_id: string
  origen_cohorte_id: string
  destino_materia_id: string
  destino_carrera_id: string
  destino_cohorte_id: string
  desde: string
  hasta?: string | null
}

/**
 * PATCH /api/v1/equipos/vigencia-general — mirrors VigenciaGeneralRequest.
 * Updates desde/hasta for ALL active asignaciones of the tripleta.
 */
export interface VigenciaGeneralRequest {
  materia_id: string
  carrera_id: string
  cohorte_id: string
  desde: string
  hasta?: string | null
}

/**
 * Query params for GET /api/v1/equipos — mirrors EquipoQuery.
 * Tripleta obligatoria + optional filters.
 */
export interface EquipoQueryParams {
  materia_id: string
  carrera_id: string
  cohorte_id: string
  rol?: RolAsignacion | null
  responsable_id?: string | null
}
