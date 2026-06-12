/**
 * MateriasTable — ABM table for materias with client-side filter.
 * Follows CarrerasTable / AsignacionesTable pattern. < 200 LOC.
 */
import { useState, useMemo } from 'react'
import type { MateriaRead, MateriaClientFiltros } from '../types'
import { EmptyState, StatusBadge } from '@/shared/components/ui'

interface Props {
  materias: MateriaRead[]
  onEdit: (materia: MateriaRead) => void
  onDelete: (id: string) => void
  isDeleting: boolean
}

const EMPTY_FILTROS: MateriaClientFiltros = {}

function applyFiltros(list: MateriaRead[], f: MateriaClientFiltros): MateriaRead[] {
  return list.filter((m) => {
    if (f.nombre && f.nombre.trim() !== '') {
      if (!m.nombre.toLowerCase().includes(f.nombre.trim().toLowerCase())) return false
    }
    if (f.estado) {
      if (m.estado !== f.estado) return false
    }
    return true
  })
}

const inputClass = 'rounded border border-gray-300 px-3 py-1.5 text-sm'

export default function MateriasTable({ materias, onEdit, onDelete, isDeleting }: Props) {
  const [filtros, setFiltros] = useState<MateriaClientFiltros>(EMPTY_FILTROS)
  const filtered = useMemo(() => applyFiltros(materias, filtros), [materias, filtros])

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
          onChange={(e) => setFiltros((f) => ({ ...f, estado: e.target.value as MateriaClientFiltros['estado'] }))}
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
        <div data-testid="materias-empty">
          <EmptyState title="No hay materias para los filtros aplicados." />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">Código</th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">Nombre</th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">Estado</th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((m) => (
                <tr key={m.id}>
                  <td className="px-4 py-3 font-mono text-xs text-gray-700">{m.codigo}</td>
                  <td className="px-4 py-3 text-gray-900">{m.nombre}</td>
                  <td className="px-4 py-3"><StatusBadge status={m.estado} /></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        data-testid={`btn-editar-${m.id}`}
                        onClick={() => onEdit(m)}
                        className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        data-testid={`btn-baja-${m.id}`}
                        onClick={() => onDelete(m.id)}
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
