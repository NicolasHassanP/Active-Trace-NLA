/**
 * Wire types for Coloquios feature — mirrors C-14 backend schemas.
 * No `any`. All unions are explicit literal types.
 * Fields aligned to backend/app/schemas/evaluacion.py.
 * Task 6.1.
 */

// ---------------------------------------------------------------------------
// Enums / union types
// ---------------------------------------------------------------------------

/**
 * Maps EvaluacionTipo from backend/app/models/evaluacion.py.
 */
export type EvaluacionTipo = 'Coloquio' | 'TP' | 'Parcial' | 'Recuperatorio'

/**
 * Maps ReservaEstado from backend/app/models/evaluacion.py.
 */
export type ReservaEstado = 'Activa' | 'Cancelada'

// ---------------------------------------------------------------------------
// Response types — matches exactly the backend Read schemas
// ---------------------------------------------------------------------------

/**
 * Mirrors MetricasRead — panel de métricas globales del módulo (F7.1).
 */
export interface MetricasRead {
  convocatorias_activas: number
  alumnos_cargados: number
  reservas_activas: number
  notas_registradas: number
}

/**
 * Mirrors ConvocatoriaMetricasRead — convocatoria with derived metrics (F7.4).
 */
export interface ConvocatoriaMetricasRead {
  id: string
  materia_id: string
  cohorte_id: string
  tipo: EvaluacionTipo
  instancia: string
  cerrada: boolean
  convocados: number
  reservas_activas: number
  cupos_libres: number
}

/**
 * Mirrors TurnoRead — a reservable slot within a convocatoria.
 */
export interface TurnoRead {
  id: string
  evaluacion_id: string
  fecha: string   // ISO date string
  cupo_total: number
  franja: string | null
}

/**
 * Mirrors ConvocatoriaRead — a convocatoria (evaluacion) record.
 */
export interface ConvocatoriaRead {
  id: string
  materia_id: string
  cohorte_id: string
  tipo: EvaluacionTipo
  instancia: string
  dias_disponibles: number
  cerrada: boolean
}

/**
 * Mirrors ConvocatoriaConTurnosRead — response on creation.
 */
export interface ConvocatoriaConTurnosRead {
  evaluacion: ConvocatoriaRead
  turnos: TurnoRead[]
}

/**
 * Mirrors AgendaItemRead — one item in the consolidated agenda (F7.5).
 */
export interface AgendaItemRead {
  reserva_id: string
  evaluacion_id: string
  turno_id: string
  fecha_turno: string   // ISO date string
  alumno_id: string
  estado: ReservaEstado
}

/**
 * Mirrors ResultadoRead — academic result for an alumno.
 */
export interface ResultadoRead {
  id: string
  evaluacion_id: string
  alumno_id: string
  nota_final: string | null
}

// ---------------------------------------------------------------------------
// Request types — for form payloads
// ---------------------------------------------------------------------------

/**
 * Mirrors TurnoRequest — a turno to include when creating a convocatoria.
 */
export interface TurnoRequest {
  fecha: string      // ISO date string
  cupo_total: number
  franja?: string | null
}

/**
 * Mirrors CrearConvocatoriaRequest.
 * tenant_id and actor identity NEVER included — travel via JWT.
 */
export interface CrearConvocatoriaRequest {
  materia_id: string
  cohorte_id: string
  tipo: EvaluacionTipo
  instancia: string
  dias_disponibles: number
  turnos: TurnoRequest[]
}

/**
 * Mirrors ImportarCandidatosRequest.
 */
export interface ImportarCandidatosRequest {
  evaluacion_id: string
  alumno_ids: string[]
}
