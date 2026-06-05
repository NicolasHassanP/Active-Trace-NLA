/**
 * tareasService — wraps C-16 Tareas API endpoints.
 * Identity/tenant never in request body — they travel via JWT (apiClient interceptor).
 * Errors are wrapped with parseDomainError for typed handling.
 * Tasks 3.2, 3.3, 3.4.
 */
import apiClient from '@/shared/services/api'
import { parseDomainError } from '@/shared/services/domainError'
import type {
  TareaRead,
  ComentarioTareaRead,
  TareaCreateRequest,
  TareaDelegarRequest,
  TareaUpdateEstadoRequest,
  ComentarioTareaCreateRequest,
  TareasAdminParams,
} from '../types'

// ---------------------------------------------------------------------------
// Task 3.2 — read / list helpers
// ---------------------------------------------------------------------------

/**
 * GET /api/v1/tareas/mias
 * Returns tasks assigned to the authenticated user.
 */
export async function listarMias(): Promise<TareaRead[]> {
  try {
    const response = await apiClient.get<TareaRead[]>('/tareas/mias')
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * GET /api/v1/tareas/{tarea_id}
 * Returns detail of a single task (ownership enforced by backend).
 */
export async function detalleTarea(tareaId: string): Promise<TareaRead> {
  try {
    const response = await apiClient.get<TareaRead>(`/tareas/${tareaId}`)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * GET /api/v1/tareas/admin
 * Lists all tenant tasks with optional filters. Requires tareas:gestionar.
 * Null/undefined filter values are omitted from the request.
 */
export async function listarAdmin(params: TareasAdminParams): Promise<TareaRead[]> {
  try {
    const query: Record<string, string> = {}
    if (params.asignado_a != null) query['asignado_a'] = params.asignado_a
    if (params.asignado_por != null) query['asignado_por'] = params.asignado_por
    if (params.materia_id != null) query['materia_id'] = params.materia_id
    if (params.estado != null) query['estado'] = params.estado
    if (params.q != null) query['q'] = params.q

    const response = await apiClient.get<TareaRead[]>('/tareas/admin', { params: query })
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Task 3.3 — write helpers (alta + delegación)
// ---------------------------------------------------------------------------

/**
 * POST /api/v1/tareas
 * Creates and assigns a new task. Requires tareas:gestionar.
 * Returns the created TareaRead (estado initial = Pendiente).
 */
export async function crearTarea(body: TareaCreateRequest): Promise<TareaRead> {
  try {
    const response = await apiClient.post<TareaRead>('/tareas', body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * POST /api/v1/tareas/{tarea_id}/delegar
 * Delegates a task to another docente. Requires tareas:gestionar.
 * Returns the updated TareaRead with the new asignado_a.
 */
export async function delegarTarea(tareaId: string, body: TareaDelegarRequest): Promise<TareaRead> {
  try {
    const response = await apiClient.post<TareaRead>(`/tareas/${tareaId}/delegar`, body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

// ---------------------------------------------------------------------------
// Task 3.4 — state + comments
// ---------------------------------------------------------------------------

/**
 * PATCH /api/v1/tareas/{tarea_id}/estado
 * Changes the task state according to the workflow matrix.
 * Returns the updated TareaRead.
 */
export async function cambiarEstado(
  tareaId: string,
  body: TareaUpdateEstadoRequest,
): Promise<TareaRead> {
  try {
    const response = await apiClient.patch<TareaRead>(`/tareas/${tareaId}/estado`, body)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * GET /api/v1/tareas/{tarea_id}/comentarios
 * Returns the comment thread for a task (ownership enforced by backend).
 */
export async function listarComentarios(tareaId: string): Promise<ComentarioTareaRead[]> {
  try {
    const response = await apiClient.get<ComentarioTareaRead[]>(`/tareas/${tareaId}/comentarios`)
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}

/**
 * POST /api/v1/tareas/{tarea_id}/comentarios
 * Adds a comment to the task thread (ownership enforced by backend).
 * Returns the created ComentarioTareaRead.
 */
export async function agregarComentario(
  tareaId: string,
  body: ComentarioTareaCreateRequest,
): Promise<ComentarioTareaRead> {
  try {
    const response = await apiClient.post<ComentarioTareaRead>(
      `/tareas/${tareaId}/comentarios`,
      body,
    )
    return response.data
  } catch (err) {
    throw parseDomainError(err)
  }
}
