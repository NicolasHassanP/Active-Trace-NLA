/**
 * MonitorTable — renders the list of MonitorFila rows.
 * Task 4.5. < 200 LOC.
 */
import type { MonitorFila } from '../types'
import { EmptyState, StatusBadge } from '@/shared/components/ui'

interface Props {
  filas: MonitorFila[]
}

export default function MonitorTable({ filas }: Props) {
  if (filas.length === 0) {
    return (
      <div data-testid="monitor-empty">
        <EmptyState
          title="Sin resultados"
          description="No se encontraron registros con los filtros aplicados."
        />
      </div>
    )
  }

  return (
    <div data-testid="monitor-table" className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Padrón</th>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Estado</th>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Aprobadas</th>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Faltantes</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {filas.map((fila) => (
            <tr key={fila.entrada_padron_id} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-gray-900">{fila.entrada_padron_id}</td>
              <td className="px-4 py-3">
                <StatusBadge status={fila.estado} />
              </td>
              <td className="px-4 py-3 text-gray-700">{fila.aprobadas}</td>
              <td className="px-4 py-3 text-gray-700">{fila.faltantes}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
