/**
 * AsignacionesTable — displays a list of AsignacionRead rows with filters.
 * Filters are controlled by the parent (onFilter / onClear).
 * Actions: edit (pencil), delete (trash) — callbacks to parent.
 * < 200 LOC. Tailwind only.
 */
import { useState } from 'react'
import type { AsignacionRead, AsignacionFiltros, RolAsignacion } from '../types'
import { ROLES_ASIGNACION } from '../types'
import { Button, EmptyState, StatusBadge } from '@/shared/components/ui'

interface Props {
  asignaciones: AsignacionRead[]
  onFilter: (filtros: AsignacionFiltros) => void
  onClear: () => void
  onEdit: (asignacion: AsignacionRead) => void
  onDelete: (id: string) => void
  isDeleting: boolean
}

const selectClass =
  'rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return iso.slice(0, 10)
}

export default function AsignacionesTable({
  asignaciones,
  onFilter,
  onClear,
  onEdit,
  onDelete,
  isDeleting,
}: Props) {
  const [rol, setRol] = useState<RolAsignacion | ''>('')

  function handleFilter() {
    onFilter({ rol: rol || null })
  }

  function handleClear() {
    setRol('')
    onClear()
  }

  return (
    <div className="space-y-4">
      <div data-testid="asignaciones-filters" className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600" htmlFor="filtro-rol">
            Rol
          </label>
          <select
            id="filtro-rol"
            value={rol}
            onChange={(e) => setRol(e.target.value as RolAsignacion | '')}
            className={selectClass}
          >
            <option value="">Todos</option>
            {ROLES_ASIGNACION.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>

        <Button variant="primary" size="sm" onClick={handleFilter}>
          Filtrar
        </Button>
        <Button variant="secondary" size="sm" onClick={handleClear}>
          Limpiar filtros
        </Button>
      </div>

      {asignaciones.length === 0 ? (
        <div data-testid="asignaciones-empty">
          <EmptyState title="No hay asignaciones para los filtros aplicados." />
        </div>
      ) : (
        <div data-testid="asignaciones-table" className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">
                  Usuario
                </th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">
                  Rol
                </th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">
                  Desde
                </th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">
                  Hasta
                </th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">
                  Vigencia
                </th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {asignaciones.map((a) => (
                <tr key={a.id}>
                  <td className="px-4 py-3">
                    {a.usuario_nombre
                      ? (
                        <span>
                          <span className="text-gray-900">{a.usuario_nombre} {a.usuario_apellidos}</span>
                          <span className="block font-mono text-xs text-gray-400">{a.usuario_id.slice(0, 8)}…</span>
                        </span>
                      )
                      : (
                        <span className="font-mono text-xs text-gray-500">{a.usuario_id.slice(0, 8)}…</span>
                      )
                    }
                  </td>
                  <td className="px-4 py-3 text-gray-900">{a.rol}</td>
                  <td className="px-4 py-3 text-gray-700">{formatDate(a.desde)}</td>
                  <td className="px-4 py-3 text-gray-700">{formatDate(a.hasta)}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={a.estado_vigencia} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        data-testid={`btn-editar-${a.id}`}
                        onClick={() => onEdit(a)}
                        className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        data-testid={`btn-baja-${a.id}`}
                        onClick={() => onDelete(a.id)}
                        disabled={isDeleting}
                        className="text-red-600 hover:text-red-800 text-sm font-medium disabled:opacity-50"
                      >
                        Dar baja
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
