/**
 * MisMateriasTable — table for F4.2 Vista de mis equipos.
 * Shows: Rol | Materia ID | Carrera | Cohorte | Comisiones | Vigencia | Estado
 * - Badge de color por estado_vigencia: verde=vigente, amarillo=futura, gris=vencida
 * - Badge de color por rol: PROFESOR=indigo, TUTOR=purple, COORDINADOR=blue, NEXO=orange
 * - IDs shown as first 8 chars of UUID (no name endpoint yet)
 * - Client-side filter by estado_vigencia (Todos / Vigentes / Futuras / Vencidas)
 * < 200 LOC.
 */
import { useState } from 'react'
import type { MisMateriasItem, RolAsignacion, EstadoVigencia, VigenciaFilter } from '../types'

interface Props {
  items: MisMateriasItem[]
}

// ---------------------------------------------------------------------------
// Badge config
// ---------------------------------------------------------------------------

const VIGENCIA_LABEL: Record<EstadoVigencia, string> = {
  vigente: 'Vigente',
  vencida: 'Vencida',
  futura: 'Futura',
}

const VIGENCIA_BADGE: Record<EstadoVigencia, string> = {
  vigente: 'text-green-700 bg-green-100',
  futura: 'text-yellow-700 bg-yellow-100',
  vencida: 'text-gray-600 bg-gray-100',
}

const ROL_BADGE: Record<RolAsignacion, string> = {
  PROFESOR: 'text-indigo-700 bg-indigo-100',
  TUTOR: 'text-purple-700 bg-purple-100',
  COORDINADOR: 'text-blue-700 bg-blue-100',
  NEXO: 'text-orange-700 bg-orange-100',
  ADMIN: 'text-red-700 bg-red-100',
  FINANZAS: 'text-teal-700 bg-teal-100',
  ALUMNO: 'text-gray-700 bg-gray-100',
}

// ---------------------------------------------------------------------------
// Filter buttons config
// ---------------------------------------------------------------------------

const FILTER_OPTIONS: { value: VigenciaFilter; label: string }[] = [
  { value: 'todos', label: 'Todos' },
  { value: 'vigente', label: 'Vigentes' },
  { value: 'futura', label: 'Futuras' },
  { value: 'vencida', label: 'Vencidas' },
]

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Returns first 8 chars of a UUID or '—' when null */
function shortId(id: string | null): string {
  if (!id) return '—'
  return id.length > 8 ? id.slice(0, 8) : id
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function MisMateriasTable({ items }: Props) {
  const [filter, setFilter] = useState<VigenciaFilter>('todos')

  const filtered =
    filter === 'todos' ? items : items.filter((i) => i.estado_vigencia === filter)

  return (
    <div className="space-y-4">
      {/* Filter buttons */}
      <div role="group" aria-label="Filtrar por estado de vigencia" className="flex flex-wrap gap-2">
        {FILTER_OPTIONS.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setFilter(value)}
            aria-pressed={filter === value}
            className={[
              'rounded-full px-3 py-1 text-xs font-medium transition-colors',
              filter === value
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
            ].join(' ')}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Empty state */}
      {filtered.length === 0 && (
        <p data-testid="materias-empty" className="text-sm text-gray-500 py-4">
          {filter === 'todos'
            ? 'No tenés asignaciones actualmente.'
            : `No tenés asignaciones con estado "${VIGENCIA_LABEL[filter as EstadoVigencia] ?? filter}".`}
        </p>
      )}

      {/* Table */}
      {filtered.length > 0 && (
        <div data-testid="mis-materias-table" className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-4 py-3 text-left font-medium text-gray-600">Rol</th>
                <th scope="col" className="px-4 py-3 text-left font-medium text-gray-600">Materia</th>
                <th scope="col" className="px-4 py-3 text-left font-medium text-gray-600">Carrera</th>
                <th scope="col" className="px-4 py-3 text-left font-medium text-gray-600">Cohorte</th>
                <th scope="col" className="px-4 py-3 text-left font-medium text-gray-600">Comisiones</th>
                <th scope="col" className="px-4 py-3 text-left font-medium text-gray-600">Vigencia</th>
                <th scope="col" className="px-4 py-3 text-left font-medium text-gray-600">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filtered.map((item) => (
                <tr key={item.asignacion_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${ROL_BADGE[item.rol] ?? 'text-gray-700 bg-gray-100'}`}
                    >
                      {item.rol}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-700">{shortId(item.materia_id)}</td>
                  <td className="px-4 py-3 font-mono text-gray-700">{shortId(item.carrera_id)}</td>
                  <td className="px-4 py-3 font-mono text-gray-700">{shortId(item.cohorte_id)}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {item.comisiones.length > 0 ? item.comisiones.join(', ') : '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                    {item.desde}
                    {item.hasta ? ` → ${item.hasta}` : ' → abierta'}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${VIGENCIA_BADGE[item.estado_vigencia] ?? ''}`}
                    >
                      {VIGENCIA_LABEL[item.estado_vigencia] ?? item.estado_vigencia}
                    </span>
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
