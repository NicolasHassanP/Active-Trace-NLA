/**
 * UsuariosTable — ABM table for usuarios with client-side filter.
 * Follows CarrerasTable pattern. < 200 LOC.
 *
 * CONTRATO OQ-3: NEVER renders dni/cuil/cbu/alias_cbu columns.
 * Columns shown: nombre, apellidos, email, legajo, estado, acciones.
 * Baja (delete) requires window.confirm before calling onDelete.
 */
import { useState, useMemo } from 'react'
import type { UsuarioRead, UsuarioClientFiltros } from '../types'
import { EmptyState, StatusBadge } from '@/shared/components/ui'

interface Props {
  usuarios: UsuarioRead[]
  onEdit: (usuario: UsuarioRead) => void
  onDelete: (id: string) => void
  isDeleting: boolean
}

const EMPTY_FILTROS: UsuarioClientFiltros = {}

function applyFiltros(list: UsuarioRead[], f: UsuarioClientFiltros): UsuarioRead[] {
  return list.filter((u) => {
    if (f.nombre && f.nombre.trim() !== '') {
      const fullName = `${u.nombre} ${u.apellidos}`.toLowerCase()
      if (!fullName.includes(f.nombre.trim().toLowerCase())) return false
    }
    if (f.email && f.email.trim() !== '') {
      if (!u.email.toLowerCase().includes(f.email.trim().toLowerCase())) return false
    }
    if (f.estado) {
      if (u.estado !== f.estado) return false
    }
    return true
  })
}

const inputClass = 'rounded border border-gray-300 px-3 py-1.5 text-sm'

export default function UsuariosTable({ usuarios, onEdit, onDelete, isDeleting }: Props) {
  const [filtros, setFiltros] = useState<UsuarioClientFiltros>(EMPTY_FILTROS)
  const filtered = useMemo(() => applyFiltros(usuarios, filtros), [usuarios, filtros])

  function handleBaja(id: string) {
    if (window.confirm('¿Confirmar baja lógica del usuario? Esta acción no se puede deshacer.')) {
      onDelete(id)
    }
  }

  return (
    <div className="space-y-3">
      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <input
          type="text"
          placeholder="Filtrar por nombre…"
          value={filtros.nombre ?? ''}
          onChange={(e) => setFiltros((f) => ({ ...f, nombre: e.target.value }))}
          className={inputClass}
        />
        <input
          type="text"
          placeholder="Filtrar por email…"
          value={filtros.email ?? ''}
          onChange={(e) => setFiltros((f) => ({ ...f, email: e.target.value }))}
          className={inputClass}
        />
        <select
          value={filtros.estado ?? ''}
          onChange={(e) => setFiltros((f) => ({ ...f, estado: e.target.value as UsuarioClientFiltros['estado'] }))}
          className={inputClass}
        >
          <option value="">Todos los estados</option>
          <option value="activo">Activo</option>
          <option value="inactivo">Inactivo</option>
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
        <div data-testid="usuarios-empty">
          <EmptyState title="No hay usuarios para los filtros aplicados." />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">Nombre</th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">Apellidos</th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">Email</th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">Legajo</th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">Estado</th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">Asignaciones</th>
                <th className="px-4 py-3 text-left font-medium uppercase tracking-wider text-gray-500">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((u) => (
                <tr key={u.id}>
                  <td className="px-4 py-3 text-gray-900">{u.nombre}</td>
                  <td className="px-4 py-3 text-gray-900">{u.apellidos}</td>
                  <td className="px-4 py-3 text-gray-700">{u.email}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">{u.legajo ?? '—'}</td>
                  <td className="px-4 py-3"><StatusBadge status={u.estado} /></td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{u.asignaciones.length}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        data-testid={`btn-editar-${u.id}`}
                        onClick={() => onEdit(u)}
                        className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        data-testid={`btn-baja-${u.id}`}
                        onClick={() => handleBaja(u.id)}
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
