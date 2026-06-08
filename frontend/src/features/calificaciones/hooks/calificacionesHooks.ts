/**
 * Calificaciones TanStack Query hooks — queries and mutations for all calificaciones endpoints.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  configurarUmbral,
  getNotasFinales,
  getRanking,
  getReporteMateria,
  getUmbral,
  importarCalificaciones,
  previewCalificaciones,
} from '../services/calificacionesService'
import type { ConfigurarUmbralRequest, ImportarCalificacionesRequest } from '../types'

// ---------------------------------------------------------------------------
// Calificaciones mutations
// ---------------------------------------------------------------------------

/** Mutation: upload file and get preview (actividades + filas) */
export function usePreviewCalificaciones() {
  return useMutation({
    mutationFn: (file: File) => previewCalificaciones(file),
  })
}

/** Mutation: confirm import with selected activities + filas from preview */
export function useImportarCalificaciones() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (request: ImportarCalificacionesRequest) => importarCalificaciones(request),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['ranking'] })
      void qc.invalidateQueries({ queryKey: ['reporte-materia'] })
      void qc.invalidateQueries({ queryKey: ['notas-finales'] })
      void qc.invalidateQueries({ queryKey: ['atrasados'] })
      void qc.invalidateQueries({ queryKey: ['seguimiento'] })
    },
  })
}

// ---------------------------------------------------------------------------
// Umbral queries and mutations
// ---------------------------------------------------------------------------

/** Query: get effective approval threshold for a materia */
export function useUmbral(materia_id: string) {
  return useQuery({
    queryKey: ['umbral', materia_id],
    queryFn: () => getUmbral(materia_id),
    enabled: materia_id.trim() !== '',
  })
}

/** Mutation: save or update approval threshold */
export function useConfigurarUmbral() {
  return useMutation({
    mutationFn: (request: ConfigurarUmbralRequest) => configurarUmbral(request),
  })
}

// ---------------------------------------------------------------------------
// Analisis queries
// ---------------------------------------------------------------------------

/** Query: ranking of students by approved activities */
export function useRanking(materia_id: string, actividades: string[] = []) {
  return useQuery({
    queryKey: ['ranking', materia_id, actividades],
    queryFn: () => getRanking(materia_id, actividades),
    enabled: materia_id.trim() !== '',
  })
}

/** Query: quick metrics for materia×cohorte */
export function useReporteMateria(
  materia_id: string,
  cohorte_id: string,
  actividades: string[] = [],
) {
  return useQuery({
    queryKey: ['reporte-materia', materia_id, cohorte_id, actividades],
    queryFn: () => getReporteMateria(materia_id, cohorte_id, actividades),
    enabled: materia_id.trim() !== '' && cohorte_id.trim() !== '',
  })
}

/** Query: final grades per student */
export function useNotasFinales(materia_id: string, actividades: string[] = []) {
  return useQuery({
    queryKey: ['notas-finales', materia_id, actividades],
    queryFn: () => getNotasFinales(materia_id, actividades),
    enabled: materia_id.trim() !== '',
  })
}
