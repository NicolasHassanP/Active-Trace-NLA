/**
 * Equipos TanStack Query hooks.
 * queryKey includes all active filter params for correct cache invalidation.
 * Task 1.8.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  listarMisEquipos,
  consultarEquipo,
  asignacionMasiva,
  clonarEquipo,
  vigenciaGeneral,
} from '../services/equiposService'
import type {
  AsignacionMasivaRequest,
  ClonarEquipoRequest,
  EquipoQueryParams,
  VigenciaGeneralRequest,
} from '../types'

// Query key roots for invalidation
const KEYS = {
  misEquipos: ['mis-equipos'] as const,
  equipo: (params: EquipoQueryParams) =>
    ['equipo', params.materia_id, params.carrera_id, params.cohorte_id, params.rol ?? null, params.responsable_id ?? null] as const,
}

/**
 * Query hook for GET /api/v1/equipos/mis-equipos.
 * Always enabled — returns empty array until data loads.
 */
export function useMisEquipos() {
  return useQuery({
    queryKey: KEYS.misEquipos,
    queryFn: listarMisEquipos,
  })
}

/**
 * Query hook for GET /api/v1/equipos.
 * Only fires when the full tripleta is provided.
 */
export function useEquipo(params: EquipoQueryParams) {
  return useQuery({
    queryKey: KEYS.equipo(params),
    queryFn: () => consultarEquipo(params),
    enabled: Boolean(params.materia_id && params.carrera_id && params.cohorte_id),
  })
}

/**
 * Mutation hook for POST /api/v1/equipos/asignacion-masiva.
 * On success: invalidates mis-equipos and any cached equipo query.
 */
export function useAsignacionMasiva() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: AsignacionMasivaRequest) => asignacionMasiva(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEYS.misEquipos })
      void qc.invalidateQueries({ queryKey: ['equipo'] })
    },
  })
}

/**
 * Mutation hook for POST /api/v1/equipos/clonar.
 * On success: invalidates mis-equipos and equipo queries.
 */
export function useClonarEquipo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ClonarEquipoRequest) => clonarEquipo(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEYS.misEquipos })
      void qc.invalidateQueries({ queryKey: ['equipo'] })
    },
  })
}

/**
 * Mutation hook for PATCH /api/v1/equipos/vigencia-general.
 * On success: invalidates equipo queries.
 */
export function useVigenciaGeneral() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: VigenciaGeneralRequest) => vigenciaGeneral(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['equipo'] })
      void qc.invalidateQueries({ queryKey: KEYS.misEquipos })
    },
  })
}
