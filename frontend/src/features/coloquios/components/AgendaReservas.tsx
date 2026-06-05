/**
 * AgendaReservas — displays consolidated agenda of active reservas (F7.5).
 * Task 6.10. < 200 LOC. Tailwind only.
 */
import type { AgendaItemRead } from '../types'

interface Props {
  items: AgendaItemRead[]
}

const ESTADO_COLORS: Record<string, string> = {
  activa: 'bg-green-100 text-green-800',
  cancelada: 'bg-red-100 text-red-800',
}

export default function AgendaReservas({ items }: Props) {
  if (items.length === 0) {
    return (
      <p data-testid="agenda-empty" className="text-sm text-gray-500 py-4">
        No hay reservas activas en el período.
      </p>
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
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${ESTADO_COLORS[item.estado] ?? 'bg-gray-100 text-gray-700'}`}
                >
                  {item.estado}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
