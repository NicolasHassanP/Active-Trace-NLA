/**
 * Wire types for Atrasados feature — mirrors C-11 backend schemas (snake_case).
 * No `any` — all status unions are explicit literal types.
 */

/** Estado de seguimiento de un alumno */
export type EstadoAlumno = 'atrasado' | 'al_dia' | 'sin_datos'

/** A student behind on activities — from GET /analisis/atrasados */
export interface AlumnoAtrasado {
  alumno_id: string
  nombre: string
  apellidos: string
  email: string
  actividades_faltantes: string[]
  actividades_no_aprobadas: string[]
  estado: EstadoAlumno
}

/** Aggregate metrics for a materia from GET /analisis/reporte-materia */
export interface ReporteMateria {
  materia_id: string
  cohorte_id: string
  total_alumnos: number
  total_atrasados: number
  tasa_aprobacion: number
  /** true when there is not enough data to compute metrics */
  sin_datos: boolean
}
