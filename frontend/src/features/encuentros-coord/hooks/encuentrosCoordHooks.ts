/**
 * EncuentrosCoord TanStack Query hooks.
 * queryKey MUST include ALL active filter params for correct cache isolation.
 * Task 5.5.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { crearSlot, listarInstancias, listarGuardias, getBloqueHtml } from '../services/encuentrosCoordService'
import type { CrearSlotRequest, InstanciasParams, GuardiaParams } from '../types'

// ---------------------------------------------------------------------------
// useCrearSlot — POST /api/v1/encuentros/slots
// ---------------------------------------------------------------------------

/**
 * Mutation hook for POST /api/v1/encuentros/slots.
 * On success invalidates the instancias query so the table refreshes.
 */
export function useCrearSlot() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: CrearSlotRequest) => crearSlot(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['encuentros-instancias'] })
    },
  })
}

// ---------------------------------------------------------------------------
// useInstancias — GET /api/v1/encuentros/instancias
// ---------------------------------------------------------------------------

function instanciasKey(params: InstanciasParams) {
  return ['encuentros-instancias', params.materia_id ?? null] as const
}

/**
 * Query hook for GET /api/v1/encuentros/instancias.
 * queryKey includes materia_id so different filter values produce separate cache entries.
 */
export function useInstancias(params: InstanciasParams) {
  return useQuery({
    queryKey: instanciasKey(params),
    queryFn: () => listarInstancias(params),
  })
}

// ---------------------------------------------------------------------------
// useGuardias — GET /api/v1/guardias
// ---------------------------------------------------------------------------

function guardiasKey(params: GuardiaParams) {
  return [
    'guardias',
    params.materia_id ?? null,
    params.carrera_id ?? null,
    params.cohorte_id ?? null,
    params.dia ?? null,
    params.estado ?? null,
  ] as const
}

/**
 * Query hook for GET /api/v1/guardias.
 * queryKey includes ALL filter fields so different filter combos produce separate cache entries.
 */
export function useGuardias(params: GuardiaParams) {
  return useQuery({
    queryKey: guardiasKey(params),
    queryFn: () => listarGuardias(params),
  })
}

// ---------------------------------------------------------------------------
// useBloqueHtml — GET /api/v1/encuentros/bloque-html (user-triggered)
// ---------------------------------------------------------------------------

/**
 * Mutation hook for GET /api/v1/encuentros/bloque-html.
 * Implemented as a mutation (not a query) because it is user-triggered,
 * not a background fetch. The returned HTML is ready to paste into Moodle.
 */
export function useBloqueHtml() {
  return useMutation({
    mutationFn: (materia_id?: string | null) => getBloqueHtml(materia_id),
  })
}
