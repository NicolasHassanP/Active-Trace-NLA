/**
 * Materias TanStack Query hooks — F4.2 Vista de mis equipos.
 * queryKey is stable; cache is shared across all Materias page renders.
 */
import { useQuery } from '@tanstack/react-query'
import { listarMisMaterias } from '../services/materiasService'

// Query key roots — stable, invalidation-friendly
const KEYS = {
  misMaterias: ['mis-materias'] as const,
}

/**
 * Query hook for GET /api/v1/equipos/mis-equipos (Materias view).
 * Always enabled — returns empty array until data loads.
 */
export function useMisMaterias() {
  return useQuery({
    queryKey: KEYS.misMaterias,
    queryFn: listarMisMaterias,
  })
}
