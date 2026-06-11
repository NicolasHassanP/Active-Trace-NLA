/**
 * Perfil TanStack Query hooks.
 * usePerfil — GET /api/v1/perfil (self profile, identity from JWT).
 * useUpdatePerfil — PATCH /api/v1/perfil; invalidates the perfil query on success.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getPerfil, updatePerfil } from '../services/perfilService'
import type { PerfilUpdate } from '../types'

const PERFIL_KEY = ['perfil'] as const

/**
 * Query hook for GET /api/v1/perfil. Always enabled.
 */
export function usePerfil() {
  return useQuery({
    queryKey: PERFIL_KEY,
    queryFn: getPerfil,
  })
}

/**
 * Mutation hook for PATCH /api/v1/perfil.
 * On success: invalidates the perfil query so the UI refetches fresh data.
 */
export function useUpdatePerfil() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: PerfilUpdate) => updatePerfil(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PERFIL_KEY })
    },
  })
}
