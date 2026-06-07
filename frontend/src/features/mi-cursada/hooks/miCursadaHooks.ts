/**
 * Mi Cursada TanStack Query hooks.
 * GET único para el estado académico del alumno autenticado.
 */
import { useQuery } from '@tanstack/react-query'
import { getEstadoAcademico } from '../services/miCursadaService'

const KEYS = {
  estadoAcademico: ['mi-cursada-estado'] as const,
}

/** Task 5.3 — GET /alumno/estado-academico: estado académico del alumno. */
export function useEstadoAcademico() {
  return useQuery({
    queryKey: KEYS.estadoAcademico,
    queryFn: getEstadoAcademico,
  })
}
