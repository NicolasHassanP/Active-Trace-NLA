/**
 * AsignacionesTable — displays a filtered list of AsignacionRead rows.
 * All filtering is client-side (in-memory) over the full list passed by the parent.
 * The filter bar is extracted to AsignacionesFilters.
 * Actions: edit (pencil), delete (trash) — callbacks to parent.
 * < 200 LOC. Tailwind only.
 */
import { useState, useMemo } from 'react'
import type { AsignacionRead, AsignacionClientFiltros } from '../types'
import { EmptyState, StatusBadge } from '@/shared/components/ui'
import AsignacionesFilters from './AsignacionesFilters'

interface Props {
  /** Full list — filtering applied in-memory inside this component. */
  asignaciones: AsignacionRead[]
  onEdit: (asignacion: AsignacionRead) => void
  onDelete: (id: string) => void
  isDeleting: boolean
}

const EMPTY_FILTROS: AsignacionClientFiltros = {}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return iso.slice(0, 10)
}

/** Extract sorted, distinct non-null values for a string field. */
function distinctValues(
  list: AsignacionRead[],
  field: 'materia_nombre' | 'cohorte_nombre',
): string[] {
  const set = new Set<string>()
  for (const a of list) {
    const v = a[field]
    if (v != null) set.add(v)
  }
  return Array.from(set).sort()
}

function applyFiltros(
  list: AsignacionRead[],
  f: AsignacionClientFiltros,
): AsignacionRead[] {
  return list.filter((a) => {
    // Usuario — substring case-insensitive on full name
    if (f.usuario && f.usuario.trim() !== '') {
      const fullName = `${a.usuario_nombre ?? ''} ${a.usuario_apellidos ?? ''}`.trim().toLowerCase()
      if (!fullName.includes(f.usuario.trim().toLowerCase())) return false
    }

    // Rol — exact match ('' is falsy so truthy check is sufficient)
    if (f.rol) {
      if (a.rol !== f.rol) return false
    }

    // Materia — exact match
    if (f.materia && f.materia !== '') {
      if (a.materia_nombre !== f.materia) return false
    }

    // Cohorte — exact match
    if (f.cohorte && f.cohorte !== '') {
      if (a.cohorte_nombre !== f.cohorte) return false
    }

    // Vigencia — exact match ('' is falsy so truthy check is sufficient)
    if (f.vigencia) {
      if (a.estado_vigencia !== f.vigencia) return false
    }

    // Rango sobre la columna "desde"
    if (f.desde && f.desde !== '') {
      if (a.desde < f.desde) return false
    }
    if (f.hasta && f.hasta !== '') {
      if (a.desde > f.hasta) return false
    }

    return true
  })
}

export default function AsignacionesTable({
  asignaciones,
  onEdit,
  onDelete,
  isDeleting,
}: Props) {
  const [filtros, setFiltros] = useState<AsignacionClientFiltros>(EMPTY_FILTROS)

  const materias = useMemo(() => distinctValues(asignaciones, 'materia_nombre'), [asignaciones])
  const cohortes = useMemo(() => distinctValues(asignaciones, 'cohorte_nombre'), [asignaciones])
  const filtered = useMemo(() => applyFiltros(asignaciones, filtros), [asignaciones, filtros])

  return (
    <div className="space-y-4">
      <AsignacionesFilters
        filtros={filtros}
        onChange={setFiltros}
        onClear={() => setFiltros(EMPTY_FILTROS)}
        materias={materias}
        cohortes={cohortes}
      />

      {filtered.length === 0 ? (
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
                  Materia
                </th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">
                  Cohorte
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
              {filtered.map((a) => (
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
                  <td className="px-4 py-3 text-gray-700">{a.materia_nombre ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-700">{a.cohorte_nombre ?? '—'}</td>
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
