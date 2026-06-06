/**
 * SeguimientoPage — F2.8 Monitor de seguimiento (TUTOR / PROFESOR view).
 *
 * RBAC: TUTOR, PROFESOR, COORDINADOR, ADMIN.
 * Identity always from JWT (useAuth) — never from URL params or body.
 * Backend auto-scopes: PROFESOR/TUTOR → only their students; COORD/ADMIN → all.
 *
 * Header counters: total alumnos + Y atrasados.
 * Filters: búsqueda (debounce 300ms), comisión, regional, min_cumplidas (immediate).
 *
 * < 200 LOC. No `any`. Only Tailwind.
 */
import { useState } from 'react'
import { useSeguimiento } from '../hooks/seguimientoHooks'
import SeguimientoFiltros from '../components/SeguimientoFiltros'
import SeguimientoTable from '../components/SeguimientoTable'
import type { SeguimientoParams } from '../types'

const EMPTY_PARAMS: SeguimientoParams = {}

export default function SeguimientoPage() {
  const [params, setParams] = useState<SeguimientoParams>(EMPTY_PARAMS)
  const query = useSeguimiento(params)

  const filas = query.data ?? []
  const totalAlumnos = filas.length
  const totalAtrasados = filas.filter((f) => f.estado === 'atrasado').length

  function handleFilter(newParams: SeguimientoParams) {
    setParams(newParams)
  }

  function handleClear() {
    setParams(EMPTY_PARAMS)
  }

  return (
    <div data-testid="seguimiento-panel" className="mx-auto max-w-6xl space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Seguimiento de alumnos</h1>
        {!query.isLoading && !query.isError && (
          <div
            data-testid="seguimiento-counters"
            className="flex items-center gap-3 text-sm text-gray-600"
          >
            <span>
              <span className="font-semibold text-gray-900">{totalAlumnos}</span>{' '}
              {totalAlumnos === 1 ? 'alumno' : 'alumnos'}
            </span>
            {totalAtrasados > 0 && (
              <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
                {totalAtrasados} atrasado{totalAtrasados !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Filters */}
      <SeguimientoFiltros onFilter={handleFilter} onClear={handleClear} />

      {/* Loading state */}
      {query.isLoading && (
        <p className="text-sm text-gray-500">Cargando seguimiento…</p>
      )}

      {/* Error state */}
      {query.isError && (
        <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
          Error al cargar el seguimiento. Intentá de nuevo.
        </div>
      )}

      {/* Results */}
      {!query.isLoading && !query.isError && (
        <SeguimientoTable filas={filas} />
      )}
    </div>
  )
}
