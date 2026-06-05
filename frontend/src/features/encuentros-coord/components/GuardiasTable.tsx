/**
 * GuardiasTable — displays a list of GuardiaRead rows.
 * Task 5.6. < 200 LOC. Tailwind only.
 */
import type { GuardiaRead } from '../types'

interface Props {
  guardias: GuardiaRead[]
}

const ESTADO_COLORS: Record<string, string> = {
  Pendiente: 'bg-yellow-100 text-yellow-800',
  Realizada: 'bg-green-100 text-green-800',
  Cancelada: 'bg-red-100 text-red-800',
}

export default function GuardiasTable({ guardias }: Props) {
  if (guardias.length === 0) {
    return (
      <p data-testid="guardias-empty" className="text-sm text-gray-500 py-4">
        No hay guardias para los filtros aplicados.
      </p>
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
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${ESTADO_COLORS[g.estado] ?? 'bg-gray-100 text-gray-700'}`}
                >
                  {g.estado}
                </span>
              </td>
              <td className="px-4 py-3 text-gray-600">{g.comentarios || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
