/**
 * MonitorTable — renders the list of MonitorFila rows.
 * Task 4.5. < 200 LOC.
 */
import type { MonitorFila } from '../types'

interface Props {
  filas: MonitorFila[]
}

const ESTADO_STYLES: Record<string, string> = {
  atrasado: 'bg-red-100 text-red-800',
  al_dia: 'bg-green-100 text-green-800',
  sin_datos: 'bg-gray-100 text-gray-600',
}

export default function MonitorTable({ filas }: Props) {
  if (filas.length === 0) {
    return (
      <p data-testid="monitor-empty" className="text-sm text-gray-500">
        No se encontraron registros con los filtros aplicados.
      </p>
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
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    ESTADO_STYLES[fila.estado] ?? 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {fila.estado}
                </span>
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
