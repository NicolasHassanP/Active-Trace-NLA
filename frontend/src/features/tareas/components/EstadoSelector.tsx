/**
 * EstadoSelector — dropdown for changing a Tarea state.
 * Task 3.7. < 200 LOC.
 */
import { toast } from 'sonner'
import { useCambiarEstado } from '../hooks/tareasHooks'
import type { TareaEstado } from '../types'

interface Props {
  tareaId: string
  currentEstado: TareaEstado
}

/** Valid transitions per backend workflow (D3) */
const TRANSITIONS: Record<TareaEstado, TareaEstado[]> = {
  Pendiente: ['EnProgreso', 'Resuelta', 'Cancelada'],
  EnProgreso: ['Pendiente', 'Resuelta', 'Cancelada'],
  Resuelta: ['EnProgreso'],
  Cancelada: [],
}

export default function EstadoSelector({ tareaId, currentEstado }: Props) {
  const cambiarEstadoMutation = useCambiarEstado()
  const availableTransitions = TRANSITIONS[currentEstado]

  if (availableTransitions.length === 0) {
    return (
      <span className="text-xs text-gray-400">Estado final — sin transiciones disponibles</span>
    )
  }

  function handleChange(newEstado: TareaEstado) {
    cambiarEstadoMutation.mutate(
      { tareaId, body: { estado: newEstado } },
      {
        onSuccess: () => toast.success(`Estado cambiado a ${newEstado}`),
        onError: (err) => toast.error((err as { detail?: string }).detail ?? 'Error al cambiar estado'),
      },
    )
  }

  return (
    <select
      data-testid="estado-selector"
      value={currentEstado}
      onChange={(e) => handleChange(e.target.value as TareaEstado)}
      disabled={cambiarEstadoMutation.isPending}
      className="rounded border border-gray-300 px-2 py-1 text-sm disabled:opacity-50"
    >
      <option value={currentEstado}>{currentEstado}</option>
      {availableTransitions.map((t) => (
        <option key={t} value={t}>{t}</option>
      ))}
    </select>
  )
}
