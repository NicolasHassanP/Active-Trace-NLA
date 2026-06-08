/**
 * Wire types for Monitores feature — mirrors C-11 backend schemas (snake_case).
 * No `any`. All unions are explicit literal types.
 * Fields aligned to backend/app/schemas/analisis.py (MonitorFila, MonitorFiltros).
 * Task 4.1.
 */

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

/**
 * Mirrors MonitorFila from backend/app/schemas/analisis.py.
 * One row per alumno in the monitor view.
 */
export interface ActividadResumen {
  actividad: string
  aprobado: boolean
  nota: string | null
}

export interface MonitorFila {
  entrada_padron_id: string
  estado: 'atrasado' | 'al_dia' | 'sin_datos'
  aprobadas: number
  faltantes: number
  nombre: string | null
  apellidos: string | null
  email: string | null
  comision: string | null
  regional: string | null
  actividades_detalle: ActividadResumen[]
}

// ---------------------------------------------------------------------------
// Admin estructura types (used by global-scope selector)
// ---------------------------------------------------------------------------

export interface MateriaItem {
  id: string
  codigo: string
  nombre: string
  estado: string
}

export interface CohorteItem {
  id: string
  carrera_id: string
  nombre: string
  anio: number
  estado: string
}

// ---------------------------------------------------------------------------
// Filter / param types
// ---------------------------------------------------------------------------

/**
 * Query params for GET /api/v1/analisis/monitor.
 * Mirrors MonitorFiltros (all fields optional).
 * fecha_desde/fecha_hasta: ISO datetime strings.
 */
export interface MonitorParams {
  materia_id?: string | null
  cohorte_id?: string | null
  comision?: string | null
  regional?: string | null
  busqueda?: string | null
  actividad?: string | null
  min_cumplidas?: number | null
  fecha_desde?: string | null
  fecha_hasta?: string | null
  actividades?: string[]
}
