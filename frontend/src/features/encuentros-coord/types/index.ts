/**
 * Wire types for EncuentrosCoord feature — mirrors C-13 backend schemas.
 * No `any`. All unions are explicit literal types.
 * Fields aligned to:
 *   backend/app/schemas/encuentro.py (InstanciaEncuentroRead)
 *   backend/app/schemas/guardia.py (GuardiaRead, GuardiaFiltros)
 * Task 5.1.
 */

// ---------------------------------------------------------------------------
// Encuentros — response types
// ---------------------------------------------------------------------------

/**
 * Maps InstanciaEncuentroEstado enum (backend/app/models/encuentro.py).
 * Values taken from the ORM model used by the backend.
 */
export type InstanciaEncuentroEstado =
  | 'programado'
  | 'realizado'
  | 'cancelado'
  | 'postergado'

/**
 * Mirrors InstanciaEncuentroRead from backend/app/schemas/encuentro.py.
 * One instancia per encuentro slot occurrence.
 */
export interface InstanciaEncuentroRead {
  id: string
  slot_id: string | null
  materia_id: string
  fecha: string   // ISO date string "YYYY-MM-DD"
  hora: string    // ISO time string "HH:MM:SS"
  titulo: string
  estado: InstanciaEncuentroEstado
  meet_url: string | null
  video_url: string | null
  comentario: string
}

/**
 * Query params for GET /api/v1/encuentros/instancias.
 * OQ-4 RESOLVED: endpoint accepts one optional filter: materia_id.
 */
export interface InstanciasParams {
  materia_id?: string | null
}

/**
 * Modes for CrearSlotRequest.
 * unico: fecha_unica set, cant_semanas = 0.
 * recurrente: dia_semana + fecha_inicio + cant_semanas > 0.
 */
export type SlotModo = 'unico' | 'recurrente'

/** POST /api/v1/encuentros/slots — mirrors CrearSlotRequest */
export interface CrearSlotRequest {
  materia_id: string
  titulo: string
  hora: string           // "HH:MM"
  dia_semana?: string | null
  fecha_inicio?: string | null  // YYYY-MM-DD
  cant_semanas: number
  fecha_unica?: string | null   // YYYY-MM-DD
  meet_url?: string | null
  vig_desde?: string | null
  vig_hasta?: string | null
}

/** POST /api/v1/encuentros/slots — mirrors CrearSlotResponse */
export interface CrearSlotResponse {
  slot: { id: string; [key: string]: unknown }
  instancias: InstanciaEncuentroRead[]
}

// ---------------------------------------------------------------------------
// Guardias — response types
// ---------------------------------------------------------------------------

/**
 * Maps DiaSemana enum from backend/app/models/encuentro.py.
 */
export type DiaSemana =
  | 'lunes'
  | 'martes'
  | 'miercoles'
  | 'jueves'
  | 'viernes'
  | 'sabado'
  | 'domingo'

/**
 * Maps GuardiaEstado enum from backend/app/models/encuentro.py.
 */
export type GuardiaEstado = 'Pendiente' | 'Realizada' | 'Cancelada'

/**
 * Mirrors GuardiaRead from backend/app/schemas/guardia.py.
 */
export interface GuardiaRead {
  id: string
  asignacion_id: string
  materia_id: string
  carrera_id: string
  cohorte_id: string
  dia: DiaSemana
  horario: string
  estado: GuardiaEstado
  comentarios: string
  creada_at: string   // ISO datetime string
}

/**
 * Query params for GET /api/v1/guardias and GET /api/v1/guardias/export.
 * OQ-4 RESOLVED: materia_id, carrera_id, cohorte_id, dia, estado — all optional.
 */
export interface GuardiaParams {
  materia_id?: string | null
  carrera_id?: string | null
  cohorte_id?: string | null
  dia?: string | null
  estado?: string | null
}
