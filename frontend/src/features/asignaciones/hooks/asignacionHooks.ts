/**
 * Asignaciones TanStack Query hooks.
 * queryKey includes ALL filtros so different filter combos produce separate cache entries.
 * Invalidation uses the ['asignaciones'] prefix to refresh every filter combination.
 *
 * Permission: equipos:asignar → COORDINADOR, ADMIN
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  listarAsignaciones,
  crearAsignacion,
  editarAsignacion,
  darBajaAsignacion,
  buscarUsuariosAsignables,
} from '../services/asignacionService'
import type { AsignacionCreate, AsignacionFiltros, AsignacionUpdate } from '../types'

const ASIGNACIONES_ROOT = ['asignaciones'] as const

function asignacionesKey(filtros: AsignacionFiltros) {
  return [
    'asignaciones',
    filtros.usuario_id ?? null,
    filtros.rol ?? null,
    filtros.responsable_id ?? null,
  ] as const
}

/**
 * Query hook for GET /api/v1/asignaciones.
 * queryKey includes all filtros so different combos are cached separately.
 */
export function useAsignaciones(filtros: AsignacionFiltros) {
  return useQuery({
    queryKey: asignacionesKey(filtros),
    queryFn: () => listarAsignaciones(filtros),
  })
}

/**
 * Mutation hook for POST /api/v1/asignaciones.
 * On success invalidates the ['asignaciones'] root so every filtered list refreshes.
 */
export function useCrearAsignacion() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: AsignacionCreate) => crearAsignacion(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ASIGNACIONES_ROOT })
    },
  })
}

/**
 * Mutation hook for PATCH /api/v1/asignaciones/{id}.
 * On success invalidates the ['asignaciones'] root.
 */
export function useEditarAsignacion() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: AsignacionUpdate }) =>
      editarAsignacion(id, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ASIGNACIONES_ROOT })
    },
  })
}

/**
 * Mutation hook for DELETE /api/v1/asignaciones/{id}.
 * On success invalidates the ['asignaciones'] root.
 */
export function useDarBajaAsignacion() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => darBajaAsignacion(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ASIGNACIONES_ROOT })
    },
  })
}

/**
 * Query hook for GET /api/v1/asignaciones/usuarios?q=...
 * Searches usuarios asignables (non-PII) for the asignacion combobox.
 * Only enabled when q has at least 1 character after trim.
 * Uses placeholderData: keepPrevious to avoid flickering between keystrokes.
 */
export function useBuscarUsuariosAsignables(q: string) {
  return useQuery({
    queryKey: ['asignaciones', 'usuarios', q] as const,
    queryFn: () => buscarUsuariosAsignables(q),
    enabled: q.trim().length >= 1,
    placeholderData: (prev) => prev,
  })
}
