/**
 * useEstructuraOptions — shared hook that fetches materia, carrera and cohorte
 * lists for select dropdowns across the Setup Cuatrimestre wizard.
 *
 * Uses the same queryKeys as AsignacionMasivaForm to share TanStack Query cache.
 * < 40 LOC.
 */
import { useQuery } from '@tanstack/react-query'
import {
  listarTodasMaterias,
  listarTodosCohortes,
  listarTodasCarreras,
} from '@/features/monitores/services/monitoresService'
import type { MateriaItem, CohorteItem, CarreraItem } from '@/features/monitores/types'

export interface EstructuraOptions {
  materias: MateriaItem[]
  carreras: CarreraItem[]
  cohortes: CohorteItem[]
  isLoading: boolean
}

export function useEstructuraOptions(): EstructuraOptions {
  const materiasQuery = useQuery({
    queryKey: ['admin-materias'],
    queryFn: listarTodasMaterias,
  })

  const carrerasQuery = useQuery({
    queryKey: ['admin-carreras'],
    queryFn: listarTodasCarreras,
  })

  const cohortesQuery = useQuery({
    queryKey: ['admin-cohortes'],
    queryFn: listarTodosCohortes,
  })

  return {
    materias: materiasQuery.data ?? [],
    carreras: carrerasQuery.data ?? [],
    cohortes: cohortesQuery.data ?? [],
    isLoading: materiasQuery.isLoading || carrerasQuery.isLoading || cohortesQuery.isLoading,
  }
}
