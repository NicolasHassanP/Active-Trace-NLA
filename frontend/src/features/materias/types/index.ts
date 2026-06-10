/**
 * Wire types for Materias feature — F4.2 Vista de mis equipos.
 * Re-exports the shared assignment shape from backend C-08 schemas.
 * No `any`. All unions are explicit literal types.
 */

/** Rol de asignación — full set from backend RolAsignacion + dominio */
export type RolAsignacion =
  | 'PROFESOR'
  | 'TUTOR'
  | 'COORDINADOR'
  | 'NEXO'
  | 'ADMIN'
  | 'FINANZAS'
  | 'ALUMNO'

/** Estado de vigencia derivado — mirrors app.models.vigencia.EstadoVigencia */
export type EstadoVigencia = 'vigente' | 'vencida' | 'futura'

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

/**
 * Ítem de GET /api/v1/equipos/mis-equipos — mirrors MisEquiposItem.
 * Used by the Materias page to display F4.2 assignments.
 */
export interface MisMateriasItem {
  asignacion_id: string
  materia_id: string | null
  carrera_id: string | null
  cohorte_id: string | null
  materia_nombre: string | null
  carrera_nombre: string | null
  cohorte_nombre: string | null
  rol: RolAsignacion
  desde: string           // ISO date string
  hasta: string | null    // ISO date string or null (open-ended)
  estado_vigencia: EstadoVigencia
  comisiones: string[]
  responsable_id: string | null
}

/** Filter options for the client-side vigencia filter */
export type VigenciaFilter = 'todos' | EstadoVigencia
