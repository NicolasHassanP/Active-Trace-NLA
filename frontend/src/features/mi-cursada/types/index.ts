/**
 * Wire types for Mi Cursada feature — mirrors C-25 backend schemas (snake_case).
 * No `any`. Aligned to backend/app/schemas/alumno.py.
 */

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export type EstadoEntregaAlumno = 'aprobada' | 'con_nota' | 'sin_entrega'

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

/** Detalle de una actividad — mirrors CalificacionAlumnoRead */
export interface CalificacionAlumnoRead {
  actividad: string
  nota_numerica: string | null   // Decimal serialized as string
  nota_textual: string | null
  aprobado: boolean
  estado_entrega: EstadoEntregaAlumno
}

/** Materia cursada con avance — mirrors MateriaCursadaRead */
export interface MateriaCursadaRead {
  materia_id: string
  materia_nombre: string
  avance_pct: number
  total_actividades: number
  aprobadas: number
  calificaciones: CalificacionAlumnoRead[]
}

/** Coloquio reservado activo — mirrors ColoquioReservadoRead */
export interface ColoquioReservadoRead {
  evaluacion_id: string
  materia_nombre: string
  instancia: string
  tipo: string
  fecha: string   // ISO date string YYYY-MM-DD
  franja: string | null
}

/** Estado académico completo — mirrors EstadoAcademicoRead */
export interface EstadoAcademicoRead {
  avance_global_pct: number
  total_actividades: number
  aprobadas: number
  materias: MateriaCursadaRead[]
  coloquios_reservados: ColoquioReservadoRead[]
}
