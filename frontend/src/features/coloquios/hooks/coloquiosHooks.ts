/**
 * Coloquios TanStack Query hooks.
 * queryKey includes all active filter params for correct cache isolation.
 * Task 6.9.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  metricas,
  listarConvocatorias,
  crearConvocatoria,
  importarCandidatos,
  cerrarConvocatoria,
  agenda,
  resultados,
} from '../services/coloquiosService'
import type {
  CrearConvocatoriaRequest,
  ImportarCandidatosRequest,
} from '../types'
import type { AgendaParams } from '../services/coloquiosService'

// ---------------------------------------------------------------------------
// Query key roots
// ---------------------------------------------------------------------------

const KEYS = {
  metricas: ['coloquios-metricas'] as const,
  convocatorias: ['coloquios-convocatorias'] as const,
  agenda: (params: AgendaParams) =>
    ['coloquios-agenda', params.materia_id ?? null, params.fecha_desde ?? null, params.fecha_hasta ?? null] as const,
  resultados: (evaluacionId: string) =>
    ['coloquios-resultados', evaluacionId] as const,
}

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

/** GET /api/v1/coloquios/metricas — global metrics panel */
export function useMetricas() {
  return useQuery({
    queryKey: KEYS.metricas,
    queryFn: metricas,
  })
}

/** GET /api/v1/coloquios/convocatorias — list with derived metrics */
export function useConvocatorias() {
  return useQuery({
    queryKey: KEYS.convocatorias,
    queryFn: listarConvocatorias,
  })
}

/** GET /api/v1/coloquios/agenda — consolidated active reservas */
export function useAgenda(params: AgendaParams) {
  return useQuery({
    queryKey: KEYS.agenda(params),
    queryFn: () => agenda(params),
  })
}

/** GET /api/v1/coloquios/convocatorias/{id}/resultados — academic results */
export function useResultados(evaluacionId: string) {
  return useQuery({
    queryKey: KEYS.resultados(evaluacionId),
    queryFn: () => resultados(evaluacionId),
    enabled: Boolean(evaluacionId),
  })
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

/** POST /api/v1/coloquios/convocatorias — create convocatoria + turnos */
export function useCrearConvocatoria() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CrearConvocatoriaRequest) => crearConvocatoria(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEYS.convocatorias })
      void qc.invalidateQueries({ queryKey: KEYS.metricas })
    },
  })
}

/** POST /api/v1/coloquios/convocatorias/{id}/candidatos — import candidates */
export function useImportarCandidatos() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ evaluacionId, body }: { evaluacionId: string; body: ImportarCandidatosRequest }) =>
      importarCandidatos(evaluacionId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEYS.convocatorias })
      void qc.invalidateQueries({ queryKey: KEYS.metricas })
    },
  })
}

/** POST /api/v1/coloquios/convocatorias/{id}/cerrar — close convocatoria */
export function useCerrarConvocatoria() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (evaluacionId: string) => cerrarConvocatoria(evaluacionId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEYS.convocatorias })
      void qc.invalidateQueries({ queryKey: KEYS.metricas })
    },
  })
}
