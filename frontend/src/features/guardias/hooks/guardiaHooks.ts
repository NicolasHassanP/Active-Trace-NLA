/**
 * Guardias TanStack Query hooks.
 * queryKey includes ALL filtros so different filter combos produce separate cache entries.
 * Invalidation uses the ['guardias'] prefix to refresh every filter combination.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { listarGuardias, registrarGuardia } from '../services/guardiaService'
import type { GuardiaFiltros, RegistrarGuardiaRequest } from '../types'

const GUARDIAS_ROOT = ['guardias'] as const

function guardiasKey(filtros: GuardiaFiltros) {
  return [
    'guardias',
    filtros.materia_id ?? null,
    filtros.carrera_id ?? null,
    filtros.cohorte_id ?? null,
    filtros.dia ?? null,
    filtros.estado ?? null,
  ] as const
}

/**
 * Query hook for GET /api/v1/guardias.
 * queryKey includes all filtros so different combos are cached separately.
 */
export function useGuardias(filtros: GuardiaFiltros) {
  return useQuery({
    queryKey: guardiasKey(filtros),
    queryFn: () => listarGuardias(filtros),
  })
}

/**
 * Mutation hook for POST /api/v1/guardias.
 * On success invalidates the ['guardias'] root so every filtered list refreshes.
 */
export function useRegistrarGuardia() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: RegistrarGuardiaRequest) => registrarGuardia(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: GUARDIAS_ROOT })
    },
  })
}
