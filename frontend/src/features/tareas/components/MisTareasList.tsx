/**
 * MisTareasList — displays the authenticated user's tasks.
 * Task 3.7. < 200 LOC.
 */
import type { TareaRead } from '../types'

interface Props {
  tareas: TareaRead[]
}

const ESTADO_STYLES: Record<string, string> = {
  Pendiente: 'bg-yellow-100 text-yellow-800',
  EnProgreso: 'bg-blue-100 text-blue-800',
  Resuelta: 'bg-green-100 text-green-800',
  Cancelada: 'bg-gray-100 text-gray-600',
}

export default function MisTareasList({ tareas }: Props) {
  if (tareas.length === 0) {
    return (
      <p data-testid="mis-tareas-empty" className="text-sm text-gray-500">
        No hay tareas asignadas.
      </p>
    )
  }

  return (
    <ul data-testid="mis-tareas-list" className="divide-y divide-gray-100 rounded-lg border border-gray-200">
      {tareas.map((tarea) => (
        <li key={tarea.id} className="flex items-start justify-between gap-4 p-4">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">{tarea.descripcion}</p>
            {tarea.materia_id && (
              <p className="mt-0.5 text-xs text-gray-500">Materia: {tarea.materia_id}</p>
            )}
            <p className="mt-0.5 text-xs text-gray-400">
              Asignada por: {tarea.asignado_por}
            </p>
          </div>
          <span
            className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
              ESTADO_STYLES[tarea.estado] ?? 'bg-gray-100 text-gray-600'
            }`}
          >
            {tarea.estado}
          </span>
        </li>
      ))}
    </ul>
  )
}
