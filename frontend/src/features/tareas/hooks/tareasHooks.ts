/**
 * Tareas TanStack Query hooks.
 * queryKey includes all active filter params for correct cache invalidation.
 * Task 3.6.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  listarMias,
  detalleTarea,
  listarAdmin,
  crearTarea,
  delegarTarea,
  cambiarEstado,
  listarComentarios,
  agregarComentario,
} from '../services/tareasService'
import type {
  TareaCreateRequest,
  TareaDelegarRequest,
  TareaUpdateEstadoRequest,
  ComentarioTareaCreateRequest,
  TareasAdminParams,
} from '../types'

// Query key roots for invalidation
const KEYS = {
  misTareas: ['mis-tareas'] as const,
  tareasAdmin: (params: TareasAdminParams) =>
    [
      'tareas-admin',
      params.asignado_a ?? null,
      params.asignado_por ?? null,
      params.materia_id ?? null,
      params.estado ?? null,
      params.q ?? null,
    ] as const,
  detalle: (id: string) => ['tarea-detalle', id] as const,
  comentarios: (tareaId: string) => ['tarea-comentarios', tareaId] as const,
}

/**
 * Query hook for GET /api/v1/tareas/mias.
 * Always enabled — returns empty array until data loads.
 */
export function useMisTareas() {
  return useQuery({
    queryKey: KEYS.misTareas,
    queryFn: listarMias,
  })
}

/**
 * Query hook for GET /api/v1/tareas/admin.
 * queryKey includes ALL active filters for correct caching.
 */
export function useTareasAdmin(params: TareasAdminParams) {
  return useQuery({
    queryKey: KEYS.tareasAdmin(params),
    queryFn: () => listarAdmin(params),
  })
}

/**
 * Query hook for GET /api/v1/tareas/{id}.
 * Only fires when a valid tareaId is provided.
 */
export function useDetalleTarea(tareaId: string) {
  return useQuery({
    queryKey: KEYS.detalle(tareaId),
    queryFn: () => detalleTarea(tareaId),
    enabled: Boolean(tareaId),
  })
}

/**
 * Query hook for GET /api/v1/tareas/{id}/comentarios.
 */
export function useComentariosTarea(tareaId: string) {
  return useQuery({
    queryKey: KEYS.comentarios(tareaId),
    queryFn: () => listarComentarios(tareaId),
    enabled: Boolean(tareaId),
  })
}

/**
 * Mutation hook for POST /api/v1/tareas.
 * On success: invalidates mis-tareas and admin list.
 */
export function useCrearTarea() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: TareaCreateRequest) => crearTarea(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEYS.misTareas })
      void qc.invalidateQueries({ queryKey: ['tareas-admin'] })
    },
  })
}

/**
 * Mutation hook for POST /api/v1/tareas/{id}/delegar.
 * On success: invalidates mis-tareas, admin list, and task detail.
 */
export function useDelegarTarea() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ tareaId, body }: { tareaId: string; body: TareaDelegarRequest }) =>
      delegarTarea(tareaId, body),
    onSuccess: (_data, { tareaId }) => {
      void qc.invalidateQueries({ queryKey: KEYS.misTareas })
      void qc.invalidateQueries({ queryKey: ['tareas-admin'] })
      void qc.invalidateQueries({ queryKey: KEYS.detalle(tareaId) })
    },
  })
}

/**
 * Mutation hook for PATCH /api/v1/tareas/{id}/estado.
 * On success: invalidates task detail and lists.
 */
export function useCambiarEstado() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ tareaId, body }: { tareaId: string; body: TareaUpdateEstadoRequest }) =>
      cambiarEstado(tareaId, body),
    onSuccess: (_data, { tareaId }) => {
      void qc.invalidateQueries({ queryKey: KEYS.detalle(tareaId) })
      void qc.invalidateQueries({ queryKey: KEYS.misTareas })
      void qc.invalidateQueries({ queryKey: ['tareas-admin'] })
    },
  })
}

/**
 * Mutation hook for POST /api/v1/tareas/{id}/comentarios.
 * On success: invalidates the comment thread for the task.
 */
export function useAgregarComentario() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ tareaId, body }: { tareaId: string; body: ComentarioTareaCreateRequest }) =>
      agregarComentario(tareaId, body),
    onSuccess: (_data, { tareaId }) => {
      void qc.invalidateQueries({ queryKey: KEYS.comentarios(tareaId) })
    },
  })
}
