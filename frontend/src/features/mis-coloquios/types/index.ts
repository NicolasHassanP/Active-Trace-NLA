/**
 * Wire types for Mis Coloquios feature (HU-47).
 * Mirrors backend/app/schemas/evaluacion.py — ConvocatoriasAlumnoRead, TurnoConCupoRead.
 * No `any`. snake_case aligned to backend.
 */

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export type EvaluacionTipo = 'Parcial' | 'TP' | 'Coloquio' | 'Recuperatorio'

export type ReservaEstado = 'Activa' | 'Cancelada'

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

/** Turno con cupos disponibles derivados — mirrors TurnoConCupoRead */
export interface TurnoConCupoRead {
  id: string
  evaluacion_id: string
  fecha: string           // ISO date string YYYY-MM-DD
  cupo_total: number
  franja: string | null
  cupos_disponibles: number
}

/** Convocatoria disponible para el alumno — mirrors ConvocatoriasAlumnoRead */
export interface ConvocatoriasAlumnoRead {
  evaluacion_id: string
  materia_nombre: string
  instancia: string
  tipo: EvaluacionTipo
  turnos: TurnoConCupoRead[]
  /** UUID de la reserva activa del alumno en esta convocatoria, null si no reservó. */
  reserva_activa_id: string | null
}

// ---------------------------------------------------------------------------
// Request types
// ---------------------------------------------------------------------------

/** Payload para reservar un turno — mirrors ReservaRequest */
export interface ReservaRequest {
  turno_id: string
  evaluacion_id: string
}

// ---------------------------------------------------------------------------
// Reserva read — mirrors ReservaRead
// ---------------------------------------------------------------------------

export interface ReservaRead {
  id: string
  turno_id: string
  evaluacion_id: string
  alumno_id: string
  estado: ReservaEstado
}
