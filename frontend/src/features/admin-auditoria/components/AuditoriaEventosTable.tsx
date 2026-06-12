/**
 * AuditoriaEventosTable — paginated read-only table for audit events.
 * Pagination: offset-based. Siguiente disabled when events.length < limit.
 * Filters: desde/hasta/actor_user_id passed as query params.
 * < 200 LOC. Tailwind only. No mutations.
 */
import type { AuditEventRead, AuditoriaFiltros } from '../types'
import { EmptyState } from '@/shared/components/ui'

interface Props {
  events: AuditEventRead[]
  filtros: AuditoriaFiltros
  onFiltrosChange: (f: AuditoriaFiltros) => void
  isLoading: boolean
}

const DEFAULT_LIMIT = 50
const inputClass = 'rounded border border-gray-300 px-3 py-1.5 text-sm'

function formatDate(iso: string): string {
  return iso.slice(0, 19).replace('T', ' ')
}

export default function AuditoriaEventosTable({ events, filtros, onFiltrosChange, isLoading }: Props) {
  const limit = filtros.limit ?? DEFAULT_LIMIT
  const offset = filtros.offset ?? 0
  const hasMore = events.length >= limit
  const isFirstPage = offset === 0

  function handleAnterior() {
    onFiltrosChange({ ...filtros, offset: Math.max(0, offset - limit) })
  }

  function handleSiguiente() {
    onFiltrosChange({ ...filtros, offset: offset + limit })
  }

  return (
    <div className="space-y-3">
      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <input
          type="date"
          placeholder="Desde"
          value={filtros.desde ?? ''}
          onChange={(e) => onFiltrosChange({ ...filtros, desde: e.target.value || undefined, offset: 0 })}
          className={inputClass}
          aria-label="Desde"
        />
        <input
          type="date"
          placeholder="Hasta"
          value={filtros.hasta ?? ''}
          onChange={(e) => onFiltrosChange({ ...filtros, hasta: e.target.value || undefined, offset: 0 })}
          className={inputClass}
          aria-label="Hasta"
        />
        <input
          type="text"
          placeholder="Actor user ID"
          value={filtros.actor_user_id ?? ''}
          onChange={(e) => onFiltrosChange({ ...filtros, actor_user_id: e.target.value || undefined, offset: 0 })}
          className={inputClass}
          aria-label="Actor user ID"
        />
        <button
          type="button"
          onClick={() => onFiltrosChange({ limit, offset: 0 })}
          className="text-xs text-gray-500 hover:text-gray-700"
        >
          Limpiar
        </button>
      </div>

      {/* Loading indicator */}
      {isLoading && <p className="text-sm text-gray-500">Cargando eventos…</p>}

      {/* Empty state */}
      {!isLoading && events.length === 0 && (
        <div data-testid="auditoria-eventos-empty">
          <EmptyState title="No hay eventos de auditoría para los filtros aplicados." />
        </div>
      )}

      {/* Table */}
      {!isLoading && events.length > 0 && (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-xs">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium uppercase tracking-wider text-gray-500">Fecha</th>
                <th className="px-3 py-2 text-left font-medium uppercase tracking-wider text-gray-500">Actor</th>
                <th className="px-3 py-2 text-left font-medium uppercase tracking-wider text-gray-500">Acción</th>
                <th className="px-3 py-2 text-left font-medium uppercase tracking-wider text-gray-500">Módulo</th>
                <th className="px-3 py-2 text-left font-medium uppercase tracking-wider text-gray-500">Entidad</th>
                <th className="px-3 py-2 text-left font-medium uppercase tracking-wider text-gray-500">Resultado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {events.map((e) => (
                <tr key={e.id}>
                  <td className="px-3 py-2 font-mono text-gray-600">{formatDate(e.created_at)}</td>
                  <td className="px-3 py-2 font-mono text-gray-500">{e.actor_user_id.slice(0, 8)}…</td>
                  <td className="px-3 py-2 text-gray-900 font-medium">{e.accion}</td>
                  <td className="px-3 py-2 text-gray-700">{e.modulo}</td>
                  <td className="px-3 py-2 text-gray-700">{e.entidad_tipo}{e.entidad_id ? `:${e.entidad_id.slice(0, 6)}` : ''}</td>
                  <td className="px-3 py-2">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                      e.resultado === 'ok' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {e.resultado}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination controls */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          data-testid="btn-anterior"
          onClick={handleAnterior}
          disabled={isFirstPage}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-40"
        >
          Anterior
        </button>
        <span className="text-sm text-gray-500">
          Página {Math.floor(offset / limit) + 1}
        </span>
        <button
          type="button"
          data-testid="btn-siguiente"
          onClick={handleSiguiente}
          disabled={!hasMore}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-40"
        >
          Siguiente
        </button>
      </div>
    </div>
  )
}
