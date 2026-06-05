/**
 * MisEquiposTable — renders a table of the user's docente assignments.
 * Task 1.9. < 200 LOC.
 */
import type { MisEquiposItem } from '../types'

interface Props {
  items: MisEquiposItem[]
}

const VIGENCIA_LABEL: Record<string, string> = {
  vigente: 'Vigente',
  vencida: 'Vencida',
  futura: 'Futura',
}

const VIGENCIA_COLOR: Record<string, string> = {
  vigente: 'text-green-700 bg-green-50',
  vencida: 'text-red-700 bg-red-50',
  futura: 'text-yellow-700 bg-yellow-50',
}

export default function MisEquiposTable({ items }: Props) {
  if (items.length === 0) {
    return (
      <p data-testid="equipos-empty" className="text-sm text-gray-500 py-4">
        No tenés asignaciones actualmente.
      </p>
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
                <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${VIGENCIA_COLOR[item.estado_vigencia] ?? ''}`}>
                  {VIGENCIA_LABEL[item.estado_vigencia] ?? item.estado_vigencia}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
