/**
 * SeguimientoTable — renders SeguimientoFila rows.
 *
 * Columns: Alumno ID (short UUID) | Estado | Aprobadas | Faltantes
 * Uses StatusBadge for estado: rojo=atrasado, verde=al_dia, gris=sin_datos
 * Empty state: shown when filas.length === 0.
 *
 * < 200 LOC. No `any`. Only Tailwind.
 */
import type { SeguimientoFila } from '../types'
import { StatusBadge } from '@/shared/components/ui'

interface Props {
  filas: SeguimientoFila[]
}

const ESTADO_LABELS: Record<string, string> = {
  atrasado: 'Atrasado',
  al_dia: 'Al día',
  sin_datos: 'Sin datos',
}

/** Returns the first 8 characters of a UUID for compact display. */
function shortId(uuid: string): string {
  return uuid.slice(0, 8)
}

export default function SeguimientoTable({ filas }: Props) {
  if (filas.length === 0) {
    return (
      <p data-testid="seguimiento-empty" className="text-sm text-gray-500">
        No se encontraron alumnos con los filtros aplicados.
      </p>
    )
  }

  return (
    <div data-testid="seguimiento-table" className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Alumno ID</th>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Estado</th>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Aprobadas</th>
            <th className="px-4 py-3 text-left font-medium text-gray-700">Faltantes</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {filas.map((fila) => (
            <tr key={fila.entrada_padron_id} className="hover:bg-gray-50">
              <td
                className="px-4 py-3 font-mono text-gray-900"
                title={fila.entrada_padron_id}
              >
                {shortId(fila.entrada_padron_id)}
              </td>
              <td className="px-4 py-3">
                <StatusBadge
                  status={fila.estado}
                  label={ESTADO_LABELS[fila.estado] ?? fila.estado}
                />
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
