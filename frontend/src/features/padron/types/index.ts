/**
 * Wire types for Padrón feature — mirrors C-09 backend schemas (snake_case).
 * No `any` — all fields explicitly typed.
 */

/** A single student row returned by POST /padron/preview */
export interface PadronRowDTO {
  nombre: string
  apellidos: string
  email: string
  comision: string
  regional: string
}

/** Request body for POST /padron/activar */
export interface ActivarRequest {
  materia_id: string
  cohorte_id: string
  rows: PadronRowDTO[]
}

/** Response from POST /padron/activar — active version metadata */
export interface VersionPadronRead {
  id: string
  materia_id: string
  cohorte_id: string
  total_filas: number
  activa: boolean
  creado_en: string
}

/** Request body for POST /padron/sync-moodle */
export interface SyncMoodleRequest {
  course_id: string
  materia_id: string
  cohorte_id: string
}
