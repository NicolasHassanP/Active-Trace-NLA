/**
 * TareasAdminTable — admin view of all tenant tasks.
 * Supports in-place accordion expansion to show ComentariosThread.
 * TareaAdminRow is extracted to keep each component under 200 LOC.
 * Task 3.7. < 200 LOC.
 */
import type { TareaRead, TareaEstado } from '../types'
import { EmptyState, Button } from '@/shared/components/ui'
import ComentariosThread from './ComentariosThread'

// ---------------------------------------------------------------------------
// Sub-component: one table row + optional accordion panel
// ---------------------------------------------------------------------------

interface RowProps {
  tarea: TareaRead
  isSelected: boolean
  onCambiarEstado: (tareaId: string, estado: TareaEstado) => void
  onSelect: (id: string | null) => void
}

function TareaAdminRow({ tarea, isSelected, onCambiarEstado, onSelect }: RowProps) {
  const estadoBadge: Record<TareaEstado, string> = {
    Pendiente: 'bg-yellow-100 text-yellow-800',
    EnProgreso: 'bg-blue-100 text-blue-800',
    Resuelta: 'bg-green-100 text-green-800',
    Cancelada: 'bg-gray-100 text-gray-600',
  }

  return (
    <>
      <tr
        className={`cursor-pointer transition-colors ${isSelected ? 'bg-indBg' : 'hover:bg-gray-50'}`}
        onClick={() => onSelect(isSelected ? null : tarea.id)}
        aria-expanded={isSelected}
      >
        <td className="max-w-xs truncate px-4 py-3 text-gray-900">{tarea.descripcion}</td>
        <td className="px-4 py-3 text-gray-600">{tarea.asignado_a_nombre ?? tarea.asignado_a}</td>
        <td className="px-4 py-3">
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${estadoBadge[tarea.estado] ?? 'bg-gray-100 text-gray-600'}`}>
            {tarea.estado}
          </span>
        </td>
        <td className="px-4 py-3">
          <div className="flex gap-2">
            {tarea.estado !== 'Cancelada' && tarea.estado !== 'Resuelta' && (
              <Button
                variant="secondary"
                size="sm"
                onClick={(e) => { e.stopPropagation(); onCambiarEstado(tarea.id, tarea.estado === 'Pendiente' ? 'EnProgreso' : 'Resuelta') }}
              >
                Avanzar
              </Button>
            )}
          </div>
        </td>
      </tr>

      {/* Accordion panel — spans full table width */}
      {isSelected && (
        <tr data-testid={`comentarios-panel-${tarea.id}`}>
          <td colSpan={4} className="border-l-2 border-ind bg-indBg p-4">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-bold text-ink">Comentarios</span>
              <button
                type="button"
                onClick={() => onSelect(null)}
                className="text-xs text-mut hover:text-ink"
              >
                Cerrar
              </button>
            </div>
            <ComentariosThread tareaId={tarea.id} />
          </td>
        </tr>
      )}
    </>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface Props {
  tareas: TareaRead[]
  onCambiarEstado: (tareaId: string, estado: TareaEstado) => void
  onDelegar: (tareaId: string) => void
  selectedTareaId?: string | null
  onSelect?: (id: string | null) => void
}

export default function TareasAdminTable({ tareas, onCambiarEstado, onDelegar: _onDelegar, selectedTareaId = null, onSelect }: Props) {
  function handleSelect(id: string | null) {
    onSelect?.(id)
  }

  if (tareas.length === 0) {
    return (
      <div data-testid="tareas-admin-empty">
        <EmptyState title="No se encontraron tareas con los filtros aplicados." />
      </div>
    )
  }

  return (
    <div data-testid="tareas-admin-table" className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Descripción</th>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Asignado a</th>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Estado</th>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Acciones</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {tareas.map((tarea) => (
            <TareaAdminRow
              key={tarea.id}
              tarea={tarea}
              isSelected={selectedTareaId === tarea.id}
              onCambiarEstado={onCambiarEstado}
              onSelect={handleSelect}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}
