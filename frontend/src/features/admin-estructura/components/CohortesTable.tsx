/**
 * CohortesTable — ABM table for cohortes with client-side filter.
 * Shows vig_hasta as '—' when null (cohorte abierta). < 200 LOC.
 */
import { useState, useMemo } from 'react'
import type { CohorteRead, CohorteClientFiltros } from '../types'
import { EmptyState, StatusBadge } from '@/shared/components/ui'

interface Props {
  cohortes: CohorteRead[]
  onEdit: (cohorte: CohorteRead) => void
  onDelete: (id: string) => void
  isDeleting: boolean
}

const EMPTY_FILTROS: CohorteClientFiltros = {}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return iso.slice(0, 10)
}

function applyFiltros(list: CohorteRead[], f: CohorteClientFiltros): CohorteRead[] {
  return list.filter((c) => {
    if (f.nombre && f.nombre.trim() !== '') {
      if (!c.nombre.toLowerCase().includes(f.nombre.trim().toLowerCase())) return false
    }
    if (f.carrera_id) {
      if (c.carrera_id !== f.carrera_id) return false
    }
    if (f.estado) {
      if (c.estado !== f.estado) return false
    }
    return true
  })
}

const inputClass = 'rounded border border-gray-300 px-3 py-1.5 text-sm'

export default function CohortesTable({ cohortes, onEdit, onDelete, isDeleting }: Props) {
  const [filtros, setFiltros] = useState<CohorteClientFiltros>(EMPTY_FILTROS)
  const filtered = useMemo(() => applyFiltros(cohortes, filtros), [cohortes, filtros])

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <input
          type="text"
          placeholder="Filtrar por nombre…"
          value={filtros.nombre ?? ''}
          onChange={(e) => setFiltros((f) => ({ ...f, nombre: e.target.value }))}
          className={inputClass}
        />
        <select
          value={filtros.estado ?? ''}
          onChange={(e) => setFiltros((f) => ({ ...f, estado: e.target.value as CohorteClientFiltros['estado'] }))}
          className={inputClass}
        >
          <option value="">Todos los estados</option>
          <option value="activa">Activa</option>
          <option value="inactiva">Inactiva</option>
        </select>
        <button
          type="button"
          onClick={() => setFiltros(EMPTY_FILTROS)}
          className="text-xs text-gray-500 hover:text-gray-700"
        >
          Limpiar
        </button>
      </div>

      {filtered.length === 0 ? (
        <div data-testid="cohortes-empty">
          <EmptyState title="No hay cohortes para los filtros aplicados." />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">Nombre</th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">Año</th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">Vigencia desde</th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">Vigencia hasta</th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">Estado</th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((c) => (
                <tr key={c.id}>
                  <td className="px-4 py-3 text-gray-900">{c.nombre}</td>
                  <td className="px-4 py-3 text-gray-700">{c.anio}</td>
                  <td className="px-4 py-3 text-gray-700">{formatDate(c.vig_desde)}</td>
                  <td className="px-4 py-3 text-gray-700">{formatDate(c.vig_hasta)}</td>
                  <td className="px-4 py-3"><StatusBadge status={c.estado} /></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        data-testid={`btn-editar-${c.id}`}
                        onClick={() => onEdit(c)}
                        className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        data-testid={`btn-baja-${c.id}`}
                        onClick={() => onDelete(c.id)}
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
