/**
 * Comunicaciones TanStack Query hooks.
 * useLoteStatus implements bounded polling (OQ-2): refetchInterval active while
 * any message is in Pendiente/Enviando; stopped when all are terminal.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  previewComunicacion,
  encolarLote,
  getLote,
  aprobarLote,
  cancelarLote,
  aprobarIndividual,
  cancelarIndividual,
  getMisEnvios,
  getPendientesAprobacion,
} from '../services/comunicacionService'
import type {
  EstadoComunicacion,
  MisEnviosParams,
  PendientesAprobacionParams,
  PreviewRequest,
  EncolarRequest,
} from '../types'

const TERMINAL_STATES: EstadoComunicacion[] = ['Enviado', 'Fallido', 'Cancelado']
const POLLING_INTERVAL_MS = 4000

function isTerminalState(estado: EstadoComunicacion): boolean {
  return TERMINAL_STATES.includes(estado)
}

// ---- Mutations ----

export function usePreviewComunicacion() {
  return useMutation({
    mutationFn: (req: PreviewRequest) => previewComunicacion(req),
  })
}

export function useEncolarLote() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (req: EncolarRequest) => encolarLote(req),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['mis-envios'] })
    },
  })
}

export function useAprobarLote() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (loteId: string) => aprobarLote(loteId),
    onSuccess: (_data, loteId) => {
      void qc.invalidateQueries({ queryKey: ['lote', loteId] })
      void qc.invalidateQueries({ queryKey: ['mis-envios'] })
      void qc.invalidateQueries({ queryKey: ['pendientes-aprobacion'] })
    },
  })
}

export function useCancelarLote() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (loteId: string) => cancelarLote(loteId),
    onSuccess: (_data, loteId) => {
      void qc.invalidateQueries({ queryKey: ['lote', loteId] })
      void qc.invalidateQueries({ queryKey: ['mis-envios'] })
      void qc.invalidateQueries({ queryKey: ['pendientes-aprobacion'] })
    },
  })
}

export function useAprobarIndividual() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (comunicacionId: string) => aprobarIndividual(comunicacionId),
    onSuccess: (data) => {
      void qc.invalidateQueries({ queryKey: ['lote', data.lote_id] })
      void qc.invalidateQueries({ queryKey: ['mis-envios'] })
      void qc.invalidateQueries({ queryKey: ['pendientes-aprobacion'] })
    },
  })
}

export function useCancelarIndividual() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (comunicacionId: string) => cancelarIndividual(comunicacionId),
    onSuccess: (data) => {
      void qc.invalidateQueries({ queryKey: ['lote', data.lote_id] })
      void qc.invalidateQueries({ queryKey: ['mis-envios'] })
      void qc.invalidateQueries({ queryKey: ['pendientes-aprobacion'] })
    },
  })
}

// ---- Query: lote status with bounded polling ----

/**
 * useLoteStatus — polls GET /comunicaciones/lote/{loteId}.
 * refetchInterval is active only while at least one message is Pendiente or Enviando (OQ-2).
 * Stops automatically when all messages reach a terminal state.
 * Also exposes `isTerminal` as a computed boolean for UI use.
 */
export function useLoteStatus(loteId: string) {
  const query = useQuery({
    queryKey: ['lote', loteId],
    queryFn: () => getLote(loteId),
    enabled: Boolean(loteId),
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return POLLING_INTERVAL_MS
      const allTerminal = data.mensajes.every((m) => isTerminalState(m.estado))
      return allTerminal ? false : POLLING_INTERVAL_MS
    },
  })

  const isTerminal = query.data
    ? query.data.mensajes.every((m) => isTerminalState(m.estado))
    : false

  return { ...query, isTerminal }
}

// ---- Query: historial de envíos propios (C-27) ----

/**
 * useMisEnvios — queries GET /comunicaciones/mis-envios with optional filters.
 * queryKey includes all params so any change triggers a refetch (D5 from design.md).
 */
export function useMisEnvios(params: MisEnviosParams = {}) {
  return useQuery({
    queryKey: ['mis-envios', params],
    queryFn: () => getMisEnvios(params),
    refetchInterval: (query) => {
      const items = query.state.data?.items
      if (!items?.length) return false
      const hasActive = items.some((m) => !isTerminalState(m.estado as EstadoComunicacion))
      return hasActive ? POLLING_INTERVAL_MS : false
    },
  })
}

// ---- Query: pendientes de aprobación (COORDINADOR / ADMIN) ----

/**
 * usePendientesAprobacion — queries GET /comunicaciones/pendientes-aprobacion.
 * Returns all Pendiente messages across the tenant (no sender filter).
 * Only users with comunicacion:aprobar permission (COORDINADOR, ADMIN) can call this.
 * Controlled via the `enabled` param so non-managers skip the request entirely.
 */
export function usePendientesAprobacion(
  params: PendientesAprobacionParams = {},
  options: { enabled?: boolean } = {},
) {
  return useQuery({
    queryKey: ['pendientes-aprobacion', params],
    queryFn: () => getPendientesAprobacion(params),
    enabled: options.enabled !== false,
  })
}
