/**
 * Avisos TanStack Query hooks.
 * queryKey includes filters for correct cache invalidation.
 * Task 2.6.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  listarGestion,
  listarFeed,
  listarPendientes,
  crearAviso,
  actualizarAviso,
  eliminarAviso,
  ackAviso,
} from '../services/avisosService'
import type { ActualizarAvisoRequest, CrearAvisoRequest } from '../types'

const KEYS = {
  gestion: ['avisos-gestion'] as const,
  feed: (cohorteId?: string) => ['avisos-feed', cohorteId ?? null] as const,
  pendientes: (cohorteId?: string) => ['avisos-pendientes', cohorteId ?? null] as const,
}

/**
 * Query hook for GET /api/v1/avisos/gestion.
 * Returns ALL tenant avisos for the management panel (COORDINADOR/ADMIN).
 */
export function useAvisosGestion(enabled = true) {
  return useQuery({
    queryKey: KEYS.gestion,
    queryFn: listarGestion,
    enabled,
  })
}

/**
 * Query hook for GET /api/v1/avisos (recipient feed).
 */
export function useAvisosFeed(cohorteId?: string) {
  return useQuery({
    queryKey: KEYS.feed(cohorteId),
    queryFn: () => listarFeed(cohorteId),
  })
}

/**
 * Query hook for GET /api/v1/avisos/pendientes (pending ack feed).
 */
export function useAvisosPendientes(cohorteId?: string) {
  return useQuery({
    queryKey: KEYS.pendientes(cohorteId),
    queryFn: () => listarPendientes(cohorteId),
  })
}

/**
 * Mutation hook for POST /api/v1/avisos.
 * Invalidates gestion list on success.
 */
export function useCrearAviso() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CrearAvisoRequest) => crearAviso(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEYS.gestion })
    },
  })
}

/**
 * Mutation hook for PUT /api/v1/avisos/{id}.
 * Invalidates gestion list on success.
 */
export function useActualizarAviso() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: ActualizarAvisoRequest }) =>
      actualizarAviso(id, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEYS.gestion })
    },
  })
}

/**
 * Mutation hook for DELETE /api/v1/avisos/{id}.
 * Invalidates gestion list on success.
 */
export function useEliminarAviso() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => eliminarAviso(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEYS.gestion })
    },
  })
}

/**
 * Mutation hook for POST /api/v1/avisos/{id}/ack.
 * Invalidates both feed and pendientes on success.
 */
export function useAckAviso() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (avisoId: string) => ackAviso(avisoId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['avisos-feed'] })
      void qc.invalidateQueries({ queryKey: ['avisos-pendientes'] })
    },
  })
}
