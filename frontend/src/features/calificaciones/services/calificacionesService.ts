/**
 * calificacionesService — wraps Calificaciones + Analisis API endpoints.
 * Identity/tenant are NEVER included in request bodies — they travel via JWT (apiClient interceptor).
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type {
  CalificacionRead,
  ConfigurarUmbralDefaultRequest,
  ConfigurarUmbralRequest,
  ImportarCalificacionesRequest,
  NotaFinalAlumno,
  PreviewCalificaciones,
  RankingFila,
  ReporteMateria,
  UmbralMateriaRead,
} from '../types'

// ---------------------------------------------------------------------------
// POST /calificaciones/preview — parse file, no DB write
// ---------------------------------------------------------------------------

/**
 * Uploads an LMS export file as multipart FormData.
 * Returns detected activities and rows — no DB write.
 */
export async function previewCalificaciones(file: File): Promise<PreviewCalificaciones> {
  const form = new FormData()
  form.append('file', file)
  try {
    const response = await apiClient.post<PreviewCalificaciones>(
      '/calificaciones/preview',
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// POST /calificaciones/importar — confirm import with selected activities
// ---------------------------------------------------------------------------

/**
 * Confirms the import: persists Calificacion records for selected activities.
 * Sends the filas from preview back — no re-upload needed.
 */
export async function importarCalificaciones(
  request: ImportarCalificacionesRequest,
): Promise<CalificacionRead[]> {
  try {
    const response = await apiClient.post<CalificacionRead[]>('/calificaciones/importar', request)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// GET /calificaciones/umbral — get effective threshold for a materia
// ---------------------------------------------------------------------------

/**
 * Returns the effective approval threshold for the current user's asignacion in materia_id.
 * Falls back to 60% if no UmbralMateria is configured.
 */
export async function getUmbral(materia_id: string): Promise<UmbralMateriaRead> {
  try {
    const response = await apiClient.get<UmbralMateriaRead>('/calificaciones/umbral', {
      params: { materia_id },
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// PUT /calificaciones/umbral — configure threshold
// ---------------------------------------------------------------------------

/**
 * Saves or updates the approval threshold for the current user's materia.
 */
export async function configurarUmbral(request: ConfigurarUmbralRequest): Promise<UmbralMateriaRead> {
  try {
    const response = await apiClient.put<UmbralMateriaRead>('/calificaciones/umbral', request)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// GET /calificaciones/umbral (default scope global — ADMIN/COORDINADOR)
// ---------------------------------------------------------------------------

/**
 * Returns the default umbral for a materia (scope global ADMIN/COORDINADOR).
 * Optional cohorte_id filters to a specific cohort default.
 */
export async function getUmbralDefault(
  materia_id: string,
  cohorte_id?: string | null,
): Promise<UmbralMateriaRead> {
  try {
    const response = await apiClient.get<UmbralMateriaRead>('/calificaciones/umbral', {
      params: { materia_id, ...(cohorte_id ? { cohorte_id } : {}) },
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// PUT /calificaciones/umbral (default scope global — ADMIN/COORDINADOR)
// ---------------------------------------------------------------------------

/**
 * Saves or updates the default umbral for a materia/cohorte (scope global ADMIN).
 * Sends cohorte_id to associate the default with a specific cohort.
 */
export async function configurarUmbralDefault(
  request: ConfigurarUmbralDefaultRequest,
): Promise<UmbralMateriaRead> {
  try {
    const response = await apiClient.put<UmbralMateriaRead>('/calificaciones/umbral', request)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// GET /analisis/ranking
// ---------------------------------------------------------------------------

/**
 * Returns students ranked by approved activities count (descending).
 * Only students with at least 1 approved activity are included (RN-09).
 */
export async function getRanking(
  materia_id: string,
  actividades: string[] = [],
): Promise<RankingFila[]> {
  try {
    const response = await apiClient.get<RankingFila[]>('/analisis/ranking', {
      params: { materia_id, actividades },
      // axios serializes array params as repeated keys by default
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// GET /analisis/reporte-materia
// ---------------------------------------------------------------------------

/**
 * Returns quick consolidated metrics for a materia×cohorte.
 */
export async function getReporteMateria(
  materia_id: string,
  cohorte_id: string,
  actividades: string[] = [],
): Promise<ReporteMateria> {
  try {
    const response = await apiClient.get<ReporteMateria>('/analisis/reporte-materia', {
      params: { materia_id, cohorte_id, actividades },
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// GET /analisis/notas-finales
// ---------------------------------------------------------------------------

/**
 * Returns final grades per student (simple average of nota_numerica).
 * Includes students with no numeric grades (nota_final=null).
 */
export async function getNotasFinales(
  materia_id: string,
  actividades: string[] = [],
): Promise<NotaFinalAlumno[]> {
  try {
    const response = await apiClient.get<NotaFinalAlumno[]>('/analisis/notas-finales', {
      params: { materia_id, actividades },
    })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
