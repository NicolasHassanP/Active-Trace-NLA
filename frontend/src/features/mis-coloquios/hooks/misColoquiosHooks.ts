/**
 * Mis Coloquios TanStack Query hooks — HU-47.
 * useMisConvocatorias — lista convocatorias donde el alumno es candidato.
 * useReservarTurno    — reserva un turno; invalida mis-convocatorias + estado-academico.
 * useCancelarReserva  — cancela reserva propia; invalida los mismos keys.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { getMisConvocatorias, reservarTurno, cancelarReserva } from '../services/misColoquiosService'
import type { ReservaRequest } from '../types'

const KEYS = {
  misConvocatorias: ['mis-convocatorias'] as const,
  estadoAcademico: ['mi-cursada-estado'] as const,
}

/** Lista convocatorias disponibles donde el alumno es candidato. */
export function useMisConvocatorias() {
  return useQuery({
    queryKey: KEYS.misConvocatorias,
    queryFn: getMisConvocatorias,
  })
}

/** Reserva un turno para el alumno autenticado. */
export function useReservarTurno() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: ReservaRequest) => reservarTurno(payload),
    onSuccess: () => {
      toast.success('Turno reservado correctamente.')
      queryClient.invalidateQueries({ queryKey: KEYS.misConvocatorias })
      queryClient.invalidateQueries({ queryKey: KEYS.estadoAcademico })
    },
    onError: () => {
      toast.error('No se pudo reservar el turno. Intentá de nuevo.')
    },
  })
}

/** Cancela la reserva propia del alumno autenticado. */
export function useCancelarReserva() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (reservaId: string) => cancelarReserva(reservaId),
    onSuccess: () => {
      toast.success('Reserva cancelada.')
      queryClient.invalidateQueries({ queryKey: KEYS.misConvocatorias })
      queryClient.invalidateQueries({ queryKey: KEYS.estadoAcademico })
    },
    onError: () => {
      toast.error('No se pudo cancelar la reserva. Intentá de nuevo.')
    },
  })
}
