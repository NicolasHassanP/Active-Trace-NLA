/**
 * Wire types for Guardias feature — mirrors backend schemas exactly.
 * No `any`. All unions are explicit literal types.
 * Fields aligned to:
 *   backend/app/models/encuentro.py (DiaSemana, GuardiaEstado)
 *   backend/app/schemas/guardia.py (RegistrarGuardiaRequest, GuardiaRead, GuardiaFiltros)
 *
 * NOTE on DiaSemana values: the backend enum values are CAPITALIZED with accents
 * ('Lunes' … 'Miércoles' … 'Sábado'). The pre-existing encuentros-coord feature
 * uses lowercase ASCII values for DiaSemana — that is a bug in that feature and is
 * NOT reused here. This feature mirrors the real backend contract.
 */

/** Maps DiaSemana enum (backend/app/models/encuentro.py) — capitalized, accented. */
export type DiaSemana =
  | 'Lunes'
  | 'Martes'
  | 'Miércoles'
  | 'Jueves'
  | 'Viernes'
  | 'Sábado'
  | 'Domingo'

/** Maps GuardiaEstado enum (backend/app/models/encuentro.py). */
export type GuardiaEstado = 'Pendiente' | 'Realizada' | 'Cancelada'

/** Mirrors GuardiaRead from backend/app/schemas/guardia.py. */
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
  creada_at: string // ISO datetime string
}

/**
 * POST /api/v1/guardias body — mirrors RegistrarGuardiaRequest.
 * asignacion_id / tenant_id NEVER included — resolved from the JWT on the backend.
 * estado / comentarios are optional (backend defaults: 'Pendiente' / '').
 */
export interface RegistrarGuardiaRequest {
  materia_id: string
  carrera_id: string
  cohorte_id: string
  dia: DiaSemana
  horario: string
  estado?: GuardiaEstado
  comentarios?: string
}

/**
 * Query params for GET /api/v1/guardias and GET /api/v1/guardias/export.
 * All filters optional.
 */
export interface GuardiaFiltros {
  materia_id?: string | null
  carrera_id?: string | null
  cohorte_id?: string | null
  dia?: DiaSemana | null
  estado?: GuardiaEstado | null
}

/** Ordered list of DiaSemana values for selects. */
export const DIAS_SEMANA: DiaSemana[] = [
  'Lunes',
  'Martes',
  'Miércoles',
  'Jueves',
  'Viernes',
  'Sábado',
  'Domingo',
]

/** Ordered list of GuardiaEstado values for selects. */
export const GUARDIA_ESTADOS: GuardiaEstado[] = ['Pendiente', 'Realizada', 'Cancelada']
