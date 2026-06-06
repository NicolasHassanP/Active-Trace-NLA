/**
 * MisEquiposTable — renders a table of the user's docente assignments.
 * Task 1.9. < 200 LOC.
 */
import type { MisEquiposItem } from '../types'
import { EmptyState, StatusBadge } from '@/shared/components/ui'

interface Props {
  items: MisEquiposItem[]
}

export default function MisEquiposTable({ items }: Props) {
  if (items.length === 0) {
    return (
      <div data-testid="equipos-empty">
        <EmptyState title="Sin asignaciones" description="No tenés asignaciones actualmente." />
      </div>
    )
  }

  return (
    <div data-testid="mis-equipos-table" className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Materia</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Carrera</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Cohorte</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Rol</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Desde</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Hasta</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Estado</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {items.map((item) => (
            <tr key={item.asignacion_id} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-gray-800">{item.materia_id ?? '—'}</td>
              <td className="px-4 py-3 text-gray-800">{item.carrera_id ?? '—'}</td>
              <td className="px-4 py-3 text-gray-800">{item.cohorte_id ?? '—'}</td>
              <td className="px-4 py-3 text-gray-800">{item.rol}</td>
              <td className="px-4 py-3 text-gray-600">{item.desde}</td>
              <td className="px-4 py-3 text-gray-600">{item.hasta ?? '—'}</td>
              <td className="px-4 py-3">
                <StatusBadge status={item.estado_vigencia} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
