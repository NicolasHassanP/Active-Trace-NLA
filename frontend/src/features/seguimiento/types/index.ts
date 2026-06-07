/**
 * Wire types for Seguimiento feature — mirrors backend MonitorFila / MonitorFiltros.
 * Endpoint: GET /api/v1/analisis/monitor (auto-scoped by role on the backend).
 * TUTOR/PROFESOR → only their students; COORDINADOR/ADMIN → all.
 * No `any`. All unions are explicit literal types.
 */

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

/**
 * One row per alumno in the seguimiento view.
 * Backend returns UUIDs — no name resolution is done on the frontend.
 */
export interface SeguimientoFila {
  entrada_padron_id: string
  estado: 'atrasado' | 'al_dia' | 'sin_datos'
  aprobadas: number
  faltantes: number
  nombre: string | null
  apellidos: string | null
}

// ---------------------------------------------------------------------------
// Filter / param types
// ---------------------------------------------------------------------------

/**
 * Query params for GET /api/v1/analisis/monitor (seguimiento subset).
 * All fields are optional; null/undefined values are omitted from the request.
 */
export interface SeguimientoParams {
  materia_id?: string | null
  cohorte_id?: string | null
  busqueda?: string | null
  comision?: string | null
  regional?: string | null
  min_cumplidas?: number | null
}
