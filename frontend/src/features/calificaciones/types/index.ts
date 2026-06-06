/**
 * Wire types for Calificaciones feature — mirrors C-10/C-11 backend schemas.
 * No `any` — all fields explicitly typed.
 */

// ---------------------------------------------------------------------------
// POST /calificaciones/preview
// ---------------------------------------------------------------------------

/** Actividad detectada en el archivo importado */
export interface ActividadDetectada {
  actividad: string
  escala: 'numerica' | 'textual'
}

/** A single row from the LMS file (keyed by column name) */
export type CalificacionFila = Record<string, string | number | null>

/** Response from POST /calificaciones/preview */
export interface PreviewCalificaciones {
  actividades: ActividadDetectada[]
  filas: CalificacionFila[]
  no_en_padron: string[]
}

// ---------------------------------------------------------------------------
// POST /calificaciones/importar
// ---------------------------------------------------------------------------

/** Request body for POST /calificaciones/importar */
export interface ImportarCalificacionesRequest {
  materia_id: string
  cohorte_id: string
  actividades_seleccionadas: string[]
  filas: CalificacionFila[]
}

/** A persisted Calificacion record returned by importar */
export interface CalificacionRead {
  id: string
  entrada_padron_id: string
  materia_id: string
  actividad: string
  nota_numerica: number | null
  nota_textual: string | null
  aprobado: boolean
  origen: string
  importado_at: string | null
}

// ---------------------------------------------------------------------------
// GET/PUT /calificaciones/umbral
// ---------------------------------------------------------------------------

/** Request body for PUT /calificaciones/umbral */
export interface ConfigurarUmbralRequest {
  materia_id: string
  umbral_pct: number
  valores_aprobatorios: string[]
}

/** Response from GET/PUT /calificaciones/umbral */
export interface UmbralMateriaRead {
  id: string | null
  asignacion_id: string | null
  materia_id: string
  umbral_pct: number
  valores_aprobatorios: string[]
  is_default: boolean
}

// ---------------------------------------------------------------------------
// GET /analisis/ranking
// ---------------------------------------------------------------------------

/** A single row in the ranking of approved activities */
export interface RankingFila {
  entrada_padron_id: string
  cantidad_aprobadas: number
}

// ---------------------------------------------------------------------------
// GET /analisis/reporte-materia
// ---------------------------------------------------------------------------

/** Quick metrics report for a materia×cohorte */
export interface ReporteMateria {
  total_actividades: number
  total_alumnos: number
  total_atrasados: number
  total_aprobadas: number
  tasa_aprobacion: number
  sin_datos: boolean
}

// ---------------------------------------------------------------------------
// GET /analisis/notas-finales
// ---------------------------------------------------------------------------

/** Final grade per student (simple average of nota_numerica) */
export interface NotaFinalAlumno {
  entrada_padron_id: string
  nota_final: number | null
  actividades_consideradas: number
}
