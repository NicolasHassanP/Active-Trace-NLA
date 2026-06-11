/**
 * Padrón TanStack Query hooks — mutations for preview, activar, vaciar, syncMoodle.
 * All are mutations (not queries) as they have side effects or require user-triggered input.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  previewPadron,
  activarPadron,
  vaciarPadron,
  syncMoodlePadron,
} from '../services/padronService'
import type { ActivarRequest, SyncMoodleRequest } from '../types'

const ANALYSIS_KEYS = ['ranking', 'reporte-materia', 'notas-finales', 'atrasados', 'seguimiento']

/** Mutation: upload file and get preview rows */
export function usePreviewPadron() {
  return useMutation({
    mutationFn: (file: File) => previewPadron(file),
  })
}

/** Mutation: confirm import with previewed rows */
export function useActivarPadron() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (request: ActivarRequest) => activarPadron(request),
    onSuccess: () => {
      ANALYSIS_KEYS.forEach((key) => void qc.invalidateQueries({ queryKey: [key] }))
    },
  })
}

/** Mutation: empty the active padron for a materia×cohorte */
export function useVaciarPadron() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ materia_id, cohorte_id }: { materia_id: string; cohorte_id: string }) =>
      vaciarPadron(materia_id, cohorte_id),
    onSuccess: () => {
      ANALYSIS_KEYS.forEach((key) => void qc.invalidateQueries({ queryKey: [key] }))
    },
  })
}

/** Mutation: trigger on-demand sync from Moodle */
export function useSyncMoodlePadron() {
  return useMutation({
    mutationFn: (request: SyncMoodleRequest) => syncMoodlePadron(request),
  })
}
