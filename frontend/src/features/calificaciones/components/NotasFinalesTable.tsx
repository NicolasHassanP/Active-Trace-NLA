/**
 * NotasFinalesTable — final grades per student (F2.5) with CSV export.
 * Shows promedio de nota_numerica; alumnos sin calificaciones numéricas muestran "—".
 * < 200 LOC.
 */
import { useNotasFinales } from '../hooks/calificacionesHooks'
import type { DomainError } from '@/shared/services/domainError'
import type { NotaFinalAlumno } from '../types'

interface Props {
  materia_id: string
  actividades?: string[]
}

function exportCsv(data: NotaFinalAlumno[]) {
  const header = 'entrada_padron_id,nota_final,actividades_consideradas\n'
  const rows = data
    .map(
      (r) =>
        `${r.entrada_padron_id},${r.nota_final ?? ''},${r.actividades_consideradas}`,
    )
    .join('\n')
  const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'notas_finales.csv'
  link.click()
  URL.revokeObjectURL(url)
}

export default function NotasFinalesTable({ materia_id, actividades = [] }: Props) {
  const { data, isLoading, isError, error } = useNotasFinales(materia_id, actividades)

  if (isLoading) {
    return <p className="text-sm text-gray-500">Cargando notas finales…</p>
  }

  if (isError) {
    const de = error as DomainError
    return (
      <p role="alert" className="text-sm text-red-600">
        {de.detail ?? 'Error al cargar las notas finales'}
      </p>
    )
  }

  if (!data || data.length === 0) {
    return (
      <p className="text-sm text-gray-500 italic">
        No hay datos de notas finales para esta materia.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button
          onClick={() => exportCsv(data)}
          className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 border"
          data-testid="export-notas-csv"
        >
          Exportar CSV
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm border rounded">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left font-medium text-gray-600">ID Alumno (padrón)</th>
              <th className="px-4 py-2 text-right font-medium text-gray-600">Nota final</th>
              <th className="px-4 py-2 text-right font-medium text-gray-600">Actividades consideradas</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <tr key={row.entrada_padron_id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs text-gray-700">
                  {row.entrada_padron_id}
                </td>
                <td className="px-4 py-2 text-right font-semibold">
                  {row.nota_final != null ? Number(row.nota_final).toFixed(2) : '—'}
                </td>
                <td className="px-4 py-2 text-right text-gray-500">
                  {row.actividades_consideradas}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-xs text-gray-400">{data.length} alumno(s)</p>
      </div>
    </div>
  )
}
