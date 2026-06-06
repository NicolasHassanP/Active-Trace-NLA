/**
 * ResultadosTable — displays academic results for a convocatoria.
 * Task 6.10. < 200 LOC. Tailwind only.
 */
import type { ResultadoRead } from '../types'
import { EmptyState } from '@/shared/components/ui'

interface Props {
  resultados: ResultadoRead[]
}

export default function ResultadosTable({ resultados: rows }: Props) {
  if (rows.length === 0) {
    return (
      <div data-testid="resultados-empty">
        <EmptyState title="No hay resultados registrados." />
      </div>
    )
  }

  return (
    <div data-testid="resultados-table" className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Alumno
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
              Nota final
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {rows.map((r) => (
            <tr key={r.id}>
              <td className="px-4 py-3 text-gray-700 font-mono text-xs">{r.alumno_id}</td>
              <td className="px-4 py-3 text-gray-900 font-medium">{r.nota_final ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
