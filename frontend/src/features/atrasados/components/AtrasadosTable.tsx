/**
 * AtrasadosTable — displays students behind on activities.
 * Shows actividades_faltantes/no_aprobadas, empty state, client-side pagination. < 200 LOC.
 */
import { useState } from 'react'
import type { AlumnoAtrasado } from '../types'

const PAGE_SIZE = 20

interface Props {
  alumnos: AlumnoAtrasado[]
  selectedEmails: Set<string>
  onToggleSelect: (email: string) => void
}

export default function AtrasadosTable({ alumnos, selectedEmails, onToggleSelect }: Props) {
  const [page, setPage] = useState(0)

  if (alumnos.length === 0) {
    return (
      <div
        className="text-center py-12 text-gray-500"
        data-testid="atrasados-empty"
      >
        No hay alumnos atrasados para los filtros seleccionados.
      </div>
    )
  }

  const totalPages = Math.ceil(alumnos.length / PAGE_SIZE)
  const pageAlumnos = alumnos.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm border">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 w-8">
                <span className="sr-only">Seleccionar</span>
              </th>
              <th className="px-3 py-2 text-left font-medium text-gray-600">Alumno</th>
              <th className="px-3 py-2 text-left font-medium text-gray-600">Email</th>
              <th className="px-3 py-2 text-left font-medium text-gray-600">Actividades faltantes</th>
              <th className="px-3 py-2 text-left font-medium text-gray-600">No aprobadas</th>
            </tr>
          </thead>
          <tbody>
            {pageAlumnos.map((alumno) => (
              <tr key={alumno.alumno_id} className="border-t">
                <td className="px-3 py-2">
                  <input
                    type="checkbox"
                    checked={selectedEmails.has(alumno.email)}
                    onChange={() => onToggleSelect(alumno.email)}
                    data-testid={`select-${alumno.alumno_id}`}
                  />
                </td>
                <td className="px-3 py-2">{alumno.apellidos}, {alumno.nombre}</td>
                <td className="px-3 py-2">{alumno.email}</td>
                <td className="px-3 py-2">
                  {alumno.actividades_faltantes.length > 0
                    ? alumno.actividades_faltantes.join(', ')
                    : <span className="text-gray-400">—</span>}
                </td>
                <td className="px-3 py-2">
                  {alumno.actividades_no_aprobadas.length > 0
                    ? alumno.actividades_no_aprobadas.join(', ')
                    : <span className="text-gray-400">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center gap-2 text-sm">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-2 py-1 border rounded disabled:opacity-40"
          >
            ←
          </button>
          <span>Página {page + 1} de {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page === totalPages - 1}
            className="px-2 py-1 border rounded disabled:opacity-40"
          >
            →
          </button>
        </div>
      )}
    </div>
  )
}
