/**
 * Wire types for Setup Cuatrimestre feature.
 * This is an orchestrator wizard — no new backend endpoints.
 * All request/response types come from the reused services.
 */

/** Estado de un paso del wizard */
export type EstadoPaso = 'pendiente' | 'completado' | 'error'

/** Identificadores de cada paso del wizard en orden secuencial */
export type SetupPasoId =
  | 'cohorte'
  | 'clonar-equipo'
  | 'asignaciones'
  | 'vigencias'
  | 'programas'
  | 'fechas'
  | 'aviso-bienvenida'

/** Definición estática de un paso del wizard */
export interface SetupPaso {
  id: SetupPasoId
  label: string
  descripcion: string
}

/** Estado de un paso durante la ejecución del wizard */
export interface SetupPasoState {
  id: SetupPasoId
  estado: EstadoPaso
  error?: string | null
}

/** Estado completo del wizard */
export interface SetupWizardState {
  pasos: SetupPasoState[]
  /** Índice del paso actualmente activo (0-based) */
  pasoActivo: number
  /** true cuando todos los pasos están completados */
  completado: boolean
}

/**
 * POST /api/v1/programas — mirrors ProgramaCreate (backend/app/schemas/academico.py).
 * tenant_id NEVER in body — comes from JWT.
 */
export interface ProgramaCreateRequest {
  materia_id: string
  carrera_id: string
  cohorte_id: string
  titulo: string
  referencia_archivo: string
}

/** Response of POST /api/v1/programas — mirrors ProgramaRead */
export interface ProgramaRead {
  id: string
  tenant_id: string
  materia_id: string
  carrera_id: string
  cohorte_id: string
  titulo: string
  referencia_archivo: string
  cargado_at: string | null
  created_at: string
  updated_at: string
}

/**
 * POST /api/v1/fechas-academicas — mirrors FechaAcademicaCreate.
 * tenant_id NEVER in body — comes from JWT.
 * periodo: pattern "AAAA-N" (e.g. "2026-1").
 * numero: >= 1.
 */
export type FechaAcademicaTipo =
  | 'Parcial'
  | 'RecuperatorioParcial'
  | 'Integrador'
  | 'RecuperatorioIntegrador'
  | 'ColoquioEscrito'
  | 'ColoquioOral'
  | 'TrabajoPractico'
  | 'ExamenFinal'

export interface FechaAcademicaCreateRequest {
  materia_id: string
  cohorte_id: string
  tipo: FechaAcademicaTipo
  numero: number
  periodo: string
  fecha: string        // ISO date string "YYYY-MM-DD"
  titulo: string
}

/** Response of POST /api/v1/fechas-academicas — mirrors FechaAcademicaRead */
export interface FechaAcademicaRead {
  id: string
  tenant_id: string
  materia_id: string
  cohorte_id: string
  tipo: FechaAcademicaTipo
  numero: number
  periodo: string
  fecha: string
  titulo: string
  created_at: string
  updated_at: string
}

/** Static catalog of wizard steps in order */
export const SETUP_PASOS: SetupPaso[] = [
  {
    id: 'cohorte',
    label: 'Seleccionar / crear cohorte',
    descripcion: 'Indicar la cohorte del nuevo cuatrimestre.',
  },
  {
    id: 'clonar-equipo',
    label: 'Clonar equipo docente',
    descripcion: 'Copiar el equipo de una cohorte anterior al nuevo período.',
  },
  {
    id: 'asignaciones',
    label: 'Ajustar asignaciones',
    descripcion: 'Agregar o modificar asignaciones masivas del equipo.',
  },
  {
    id: 'vigencias',
    label: 'Ajustar vigencias',
    descripcion: 'Actualizar las fechas desde/hasta del equipo.',
  },
  {
    id: 'programas',
    label: 'Cargar programas',
    descripcion: 'Registrar referencias de programas de materias.',
  },
  {
    id: 'fechas',
    label: 'Cargar fechas académicas',
    descripcion: 'Registrar fechas de evaluaciones del cuatrimestre.',
  },
  {
    id: 'aviso-bienvenida',
    label: 'Publicar aviso de bienvenida',
    descripcion: 'Publicar un aviso de inicio de cuatrimestre a los docentes.',
  },
]
