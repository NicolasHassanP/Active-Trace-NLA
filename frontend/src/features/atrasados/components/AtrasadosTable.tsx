/**
 * AtrasadosTable — displays students behind on activities.
 * Shows actividades_faltantes/no_aprobadas, empty state, client-side pagination. < 200 LOC.
 */
import { useState } from 'react'
import type { AlumnoAtrasado } from '../types'
import { EmptyState, Button } from '@/shared/components/ui'

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
      <div data-testid="atrasados-empty">
        <EmptyState
          title="Sin alumnos atrasados"
          description="No hay alumnos atrasados para los filtros seleccionados."
        />
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
            {pageAlumnos.map((alumno) => {
            const toggleKey = alumno.email ?? alumno.entrada_padron_id
            return (
              <tr key={alumno.entrada_padron_id} className="border-t">
                <td className="px-3 py-2">
                  <input
                    type="checkbox"
                    checked={selectedEmails.has(toggleKey)}
                    onChange={() => onToggleSelect(toggleKey)}
                    data-testid={`select-${alumno.entrada_padron_id}`}
                  />
                </td>
                <td className="px-3 py-2">
                  {alumno.apellidos && alumno.nombre
                    ? `${alumno.apellidos}, ${alumno.nombre}`
                    : alumno.nombre ?? alumno.apellidos ?? '—'}
                </td>
                <td className="px-3 py-2">{alumno.email ?? '—'}</td>
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
            )
          })}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center gap-2 text-sm">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
          >
            ←
          </Button>
          <span>Página {page + 1} de {totalPages}</span>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page === totalPages - 1}
          >
            →
          </Button>
        </div>
      )}
    </div>
  )
}
