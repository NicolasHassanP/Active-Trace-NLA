/**
 * AuditoriaEventosTable — paginated read-only table for audit events.
 * Pagination: offset-based. Siguiente disabled when events.length < limit.
 * Filters: desde/hasta (sent to API) + actor name search (client-side substring).
 * Actor column: shows actor_nombre if available, falls back to "(desconocido)".
 * Entidad column: shows entidad_nombre for Materia/Carrera/Cohorte, otherwise
 *   a human-readable label for the entidad_tipo without the raw UUID.
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

/**
 * Human-readable label for entidad_tipo values that are not resolvable by name.
 * Materia/Carrera/Cohorte are resolved server-side and returned as entidad_nombre.
 */
const ENTIDAD_TIPO_LABEL: Record<string, string> = {
  FechaAcademica: 'Fecha académica',
  ProgramaMateria: 'Programa',
  Aviso: 'Aviso',
  Asignacion: 'Asignación',
  AuditEvent: 'Consulta de auditoría',
  Usuario: 'Usuario',
  Carrera: 'Carrera',
  Materia: 'Materia',
  Cohorte: 'Cohorte',
}

function entidadDisplay(event: AuditEventRead): string {
  // If the server resolved a name, use it.
  if (event.entidad_nombre) {
    const label = ENTIDAD_TIPO_LABEL[event.entidad_tipo] ?? event.entidad_tipo
    return `${label}: ${event.entidad_nombre}`
  }
  // Otherwise show a readable label for the type (no raw UUID).
  return ENTIDAD_TIPO_LABEL[event.entidad_tipo] ?? event.entidad_tipo
}

export default function AuditoriaEventosTable({ events, filtros, onFiltrosChange, isLoading }: Props) {
  const limit = filtros.limit ?? DEFAULT_LIMIT
  const offset = filtros.offset ?? 0
  const actorQ = (filtros.actor_nombre_q ?? '').toLowerCase()

  // Client-side filter on actor_nombre (substring, case-insensitive)
  const filteredEvents = actorQ
    ? events.filter((e) =>
        (e.actor_nombre ?? '').toLowerCase().includes(actorQ)
      )
    : events

  const hasMore = events.length >= limit  // based on raw page, not filtered
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
          placeholder="Buscar actor…"
          value={filtros.actor_nombre_q ?? ''}
          onChange={(e) =>
            onFiltrosChange({ ...filtros, actor_nombre_q: e.target.value || undefined })
          }
          className={inputClass}
          aria-label="Actor"
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
      {!isLoading && filteredEvents.length === 0 && (
        <div data-testid="auditoria-eventos-empty">
          <EmptyState title="No hay eventos de auditoría para los filtros aplicados." />
        </div>
      )}

      {/* Table */}
      {!isLoading && filteredEvents.length > 0 && (
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
              {filteredEvents.map((e) => (
                <tr key={e.id}>
                  <td className="px-3 py-2 font-mono text-gray-600">{formatDate(e.created_at)}</td>
                  <td className="px-3 py-2 text-gray-700">{e.actor_nombre ?? '(desconocido)'}</td>
                  <td className="px-3 py-2 text-gray-900 font-medium">{e.accion}</td>
                  <td className="px-3 py-2 text-gray-700">{e.modulo}</td>
                  <td className="px-3 py-2 text-gray-700">{entidadDisplay(e)}</td>
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
