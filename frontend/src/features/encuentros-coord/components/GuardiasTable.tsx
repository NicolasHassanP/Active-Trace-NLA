/**
 * GuardiasTable — displays a list of GuardiaRead rows.
 * Task 5.6. < 200 LOC. Tailwind only.
 */
import type { GuardiaRead } from '../types'
import { EmptyState, StatusBadge } from '@/shared/components/ui'

interface Props {
  guardias: GuardiaRead[]
}

export default function GuardiasTable({ guardias }: Props) {
  if (guardias.length === 0) {
    return (
      <div data-testid="guardias-empty">
        <EmptyState title="No hay guardias para los filtros aplicados." />
      </div>
    )
  }

  return (
    <div data-testid="guardias-table" className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Día
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Horario
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Estado
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Comentarios
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {guardias.map((g) => (
            <tr key={g.id}>
              <td className="px-4 py-3 text-gray-900 capitalize">{g.dia}</td>
              <td className="px-4 py-3 text-gray-700">{g.horario}</td>
              <td className="px-4 py-3">
                <StatusBadge status={g.estado.toLowerCase()} />
              </td>
              <td className="px-4 py-3 text-gray-600">{g.comentarios || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
