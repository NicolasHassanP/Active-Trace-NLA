/**
 * AgendaReservas — displays consolidated agenda of active reservas (F7.5).
 * Task 6.10. < 200 LOC. Tailwind only.
 */
import type { AgendaItemRead } from '../types'
import { EmptyState, StatusBadge } from '@/shared/components/ui'

interface Props {
  items: AgendaItemRead[]
}

export default function AgendaReservas({ items }: Props) {
  if (items.length === 0) {
    return (
      <div data-testid="agenda-empty">
        <EmptyState title="No hay reservas activas en el período." />
      </div>
    )
  }

  const sorted = [...items].sort((a, b) => a.fecha_turno.localeCompare(b.fecha_turno))

  return (
    <div data-testid="agenda-table" className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Fecha
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Alumno
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Estado
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {sorted.map((item) => (
            <tr key={item.reserva_id}>
              <td className="px-4 py-3 text-gray-900">{item.fecha_turno}</td>
              <td className="px-4 py-3 text-gray-700 font-mono text-xs">{item.alumno_id}</td>
              <td className="px-4 py-3">
                <StatusBadge status={item.estado} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
