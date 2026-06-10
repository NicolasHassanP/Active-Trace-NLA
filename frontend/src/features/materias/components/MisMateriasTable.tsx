/**
 * MisMateriasTable — table for F4.2 Vista de mis equipos.
 * Shows: Rol | Materia ID | Carrera | Cohorte | Comisiones | Vigencia | Estado
 * - StatusBadge for estado_vigencia: verde=vigente, amarillo=futura, gris=vencida
 * - Badge for rol: PROFESOR=indigo, TUTOR=purple, COORDINADOR=blue, NEXO=orange
 * - IDs shown as first 8 chars of UUID (no name endpoint yet)
 * - Client-side filter by estado_vigencia (Todos / Vigentes / Futuras / Vencidas)
 * < 200 LOC.
 */
import { useState } from 'react'
import type { MisMateriasItem, EstadoVigencia, VigenciaFilter } from '../types'
import type { RolAsignacion } from '../types'
import { Badge, StatusBadge } from '@/shared/components/ui'
import type { BadgeVariant } from '@/shared/components/ui'

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

// StatusBadge maps 'vigente' → green, 'futura' → yellow, 'vencida' → gray
// via its internal STATUS_COLOR_MAP. We only need to pass the status key.

const ROL_BADGE_VARIANT: Record<RolAsignacion, BadgeVariant> = {
  PROFESOR:     'indigo',
  TUTOR:        'purple',
  COORDINADOR:  'info',
  NEXO:         'orange',
  ADMIN:        'danger',
  FINANZAS:     'success',
  ALUMNO:       'gray',
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
                    <Badge variant={ROL_BADGE_VARIANT[item.rol] ?? 'gray'}>
                      {item.rol}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-gray-700">{item.materia_nombre ?? shortId(item.materia_id)}</td>
                  <td className="px-4 py-3 text-gray-700">{item.carrera_nombre ?? shortId(item.carrera_id)}</td>
                  <td className="px-4 py-3 text-gray-700">{item.cohorte_nombre ?? shortId(item.cohorte_id)}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {item.comisiones.length > 0 ? item.comisiones.join(', ') : '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                    {item.desde}
                    {item.hasta ? ` → ${item.hasta}` : ' → abierta'}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge
                      status={item.estado_vigencia}
                      label={VIGENCIA_LABEL[item.estado_vigencia] ?? item.estado_vigencia}
                    />
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
