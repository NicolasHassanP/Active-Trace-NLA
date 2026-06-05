/**
 * Padrón TanStack Query hooks — mutations for preview, activar, vaciar, syncMoodle.
 * All are mutations (not queries) as they have side effects or require user-triggered input.
 */
import { useMutation } from '@tanstack/react-query'
import {
  previewPadron,
  activarPadron,
  vaciarPadron,
  syncMoodlePadron,
} from '../services/padronService'
import type { ActivarRequest, SyncMoodleRequest } from '../types'

/** Mutation: upload file and get preview rows */
export function usePreviewPadron() {
  return useMutation({
    mutationFn: (file: File) => previewPadron(file),
  })
}

/** Mutation: confirm import with previewed rows */
export function useActivarPadron() {
  return useMutation({
    mutationFn: (request: ActivarRequest) => activarPadron(request),
  })
}

/** Mutation: empty the active padron for a materia×cohorte */
export function useVaciarPadron() {
  return useMutation({
    mutationFn: ({ materia_id, cohorte_id }: { materia_id: string; cohorte_id: string }) =>
      vaciarPadron(materia_id, cohorte_id),
  })
}

/** Mutation: trigger on-demand sync from Moodle */
export function useSyncMoodlePadron() {
  return useMutation({
    mutationFn: (request: SyncMoodleRequest) => syncMoodlePadron(request),
  })
}
