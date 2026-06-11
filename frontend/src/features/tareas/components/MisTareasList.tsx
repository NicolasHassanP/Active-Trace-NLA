/**
 * MisTareasList — displays the authenticated user's tasks.
 * Supports in-place accordion expansion to show ComentariosThread.
 * Task 3.7. < 200 LOC.
 */
import type { TareaRead } from '../types'
import { EmptyState } from '@/shared/components/ui'
import ComentariosThread from './ComentariosThread'

interface Props {
  tareas: TareaRead[]
  selectedTareaId?: string | null
  onSelect?: (id: string | null) => void
}

export default function MisTareasList({ tareas, selectedTareaId = null, onSelect }: Props) {
  function handleRowClick(tareaId: string) {
    if (!onSelect) return
    onSelect(selectedTareaId === tareaId ? null : tareaId)
  }

  if (tareas.length === 0) {
    return (
      <div data-testid="mis-tareas-empty">
        <EmptyState title="No hay tareas asignadas." />
      </div>
    )
  }

  return (
    <ul data-testid="mis-tareas-list" className="divide-y divide-gray-100 rounded-lg border border-gray-200">
      {tareas.map((tarea) => {
        const isSelected = selectedTareaId === tarea.id
        return (
          <li key={tarea.id}>
            {/* Row header — clickable */}
            <div
              role="button"
              tabIndex={0}
              aria-expanded={isSelected}
              onClick={() => handleRowClick(tarea.id)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleRowClick(tarea.id) }}
              className={`flex cursor-pointer items-start justify-between gap-4 p-4 transition-colors ${
                isSelected ? 'bg-indBg' : 'hover:bg-gray-50'
              }`}
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{tarea.descripcion}</p>
                {(tarea.materia_nombre ?? tarea.materia_id) && (
                  <p className="mt-0.5 text-xs text-gray-500">
                    Materia: {tarea.materia_nombre ?? tarea.materia_id}
                  </p>
                )}
                <p className="mt-0.5 text-xs text-gray-400">
                  Asignada por: {tarea.asignado_por_nombre ?? tarea.asignado_por}
                </p>
              </div>
              <span
                className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  {
                    Pendiente: 'bg-yellow-100 text-yellow-800',
                    EnProgreso: 'bg-blue-100 text-blue-800',
                    Resuelta: 'bg-green-100 text-green-800',
                    Cancelada: 'bg-gray-100 text-gray-600',
                  }[tarea.estado] ?? 'bg-gray-100 text-gray-600'
                }`}
              >
                {tarea.estado}
              </span>
            </div>

            {/* Accordion panel — ComentariosThread */}
            {isSelected && (
              <div
                data-testid={`comentarios-panel-${tarea.id}`}
                className="border-l-2 border-ind bg-indBg p-4"
              >
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs font-bold text-ink">Comentarios</span>
                  <button
                    type="button"
                    onClick={() => onSelect?.(null)}
                    className="text-xs text-mut hover:text-ink"
                  >
                    Cerrar
                  </button>
                </div>
                <ComentariosThread tareaId={tarea.id} />
              </div>
            )}
          </li>
        )
      })}
    </ul>
  )
}
