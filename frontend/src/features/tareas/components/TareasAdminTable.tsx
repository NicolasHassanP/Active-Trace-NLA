/**
 * TareasAdminTable — admin view of all tenant tasks.
 * Task 3.7. < 200 LOC.
 */
import type { TareaRead, TareaEstado } from '../types'
import { EmptyState, Button } from '@/shared/components/ui'

interface Props {
  tareas: TareaRead[]
  onCambiarEstado: (tareaId: string, estado: TareaEstado) => void
  onDelegar: (tareaId: string) => void
}

export default function TareasAdminTable({ tareas, onCambiarEstado, onDelegar }: Props) {
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
            <tr key={tarea.id} className="hover:bg-gray-50">
              <td className="max-w-xs truncate px-4 py-3 text-gray-900">{tarea.descripcion}</td>
              <td className="px-4 py-3 text-gray-600">{tarea.asignado_a_nombre ?? tarea.asignado_a}</td>
              <td className="px-4 py-3">
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
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
              </td>
              <td className="px-4 py-3">
                <div className="flex gap-2">
                  {tarea.estado !== 'Cancelada' && tarea.estado !== 'Resuelta' && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => onCambiarEstado(tarea.id, tarea.estado === 'Pendiente' ? 'EnProgreso' : 'Resuelta')}
                    >
                      Avanzar
                    </Button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
