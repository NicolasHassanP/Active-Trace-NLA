/**
 * RankingTable — ranking of students by approved activities count (RN-09).
 * Only students with ≥1 approved activity are shown (backend enforces this).
 * < 200 LOC.
 */
import { useRanking } from '../hooks/calificacionesHooks'
import type { DomainError } from '@/shared/services/domainError'

interface Props {
  materia_id: string
  actividades?: string[]
}

export default function RankingTable({ materia_id, actividades = [] }: Props) {
  const { data, isLoading, isError, error } = useRanking(materia_id, actividades)

  if (isLoading) {
    return <p className="text-sm text-gray-500">Cargando ranking…</p>
  }

  if (isError) {
    const de = error as unknown as DomainError
    return (
      <p role="alert" className="text-sm text-red-600">
        {de.detail ?? 'Error al cargar el ranking'}
      </p>
    )
  }

  if (!data || data.length === 0) {
    return (
      <p className="text-sm text-gray-500 italic">
        No hay alumnos con actividades aprobadas aún.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm border rounded">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left font-medium text-gray-600">#</th>
            <th className="px-4 py-2 text-left font-medium text-gray-600">ID Alumno (padrón)</th>
            <th className="px-4 py-2 text-right font-medium text-gray-600">Actividades aprobadas</th>
          </tr>
        </thead>
        <tbody>
          {data.map((fila, idx) => (
            <tr key={fila.entrada_padron_id} className="border-t hover:bg-gray-50">
              <td className="px-4 py-2 text-gray-500">{idx + 1}</td>
              <td className="px-4 py-2 font-mono text-xs text-gray-700">{fila.entrada_padron_id}</td>
              <td className="px-4 py-2 text-right font-semibold text-indigo-700">
                {fila.cantidad_aprobadas}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-gray-400">{data.length} alumno(s) en el ranking</p>
    </div>
  )
}
