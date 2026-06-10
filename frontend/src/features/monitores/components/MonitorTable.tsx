/**
 * MonitorTable — renders the list of MonitorFila rows.
 * Columns: Alumno | Email | Comisión | Regional | Estado | Actividades | Aprobadas | Faltantes
 * Task 4.5. < 200 LOC.
 */
import type { MonitorFila } from '../types'
import { EmptyState, StatusBadge } from '@/shared/components/ui'

interface Props {
  filas: MonitorFila[]
}

const ESTADO_LABELS: Record<string, string> = {
  atrasado: 'Atrasado',
  al_dia: 'Al día',
  sin_datos: 'Sin datos',
}

function nombreCompleto(fila: MonitorFila): string {
  const partes = [fila.apellidos, fila.nombre].filter(Boolean)
  return partes.length > 0 ? partes.join(', ') : fila.entrada_padron_id.slice(0, 8)
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
            <th className="px-4 py-3 text-left font-medium text-gray-700">Alumno</th>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Email</th>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Comisión</th>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Regional</th>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Estado</th>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Actividades</th>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Aprobadas</th>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Faltantes</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {filas.map((fila) => (
            <tr key={fila.entrada_padron_id} className="hover:bg-gray-50 align-top">
              <td className="px-4 py-3 text-gray-900 whitespace-nowrap">{nombreCompleto(fila)}</td>
              <td className="px-4 py-3 text-gray-500 text-xs">{fila.email ?? '—'}</td>
              <td className="px-4 py-3 text-gray-600">{fila.comision ?? '—'}</td>
              <td className="px-4 py-3 text-gray-600">{fila.regional ?? '—'}</td>
              <td className="px-4 py-3">
                <StatusBadge
                  status={fila.estado}
                  label={ESTADO_LABELS[fila.estado] ?? fila.estado}
                />
              </td>
              <td className="px-4 py-3">
                {fila.actividades_detalle.length === 0 ? (
                  <span className="text-xs text-gray-400">Sin datos</span>
                ) : (
                  <div className="flex flex-wrap gap-1">
                    {fila.actividades_detalle.map((act) => (
                      <span
                        key={act.actividad}
                        title={act.nota ?? undefined}
                        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                          act.aprobado
                            ? 'bg-green-50 text-green-700'
                            : 'bg-red-50 text-red-700'
                        }`}
                      >
                        {act.aprobado ? '✓' : '✗'} {act.actividad}
                      </span>
                    ))}
                  </div>
                )}
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
