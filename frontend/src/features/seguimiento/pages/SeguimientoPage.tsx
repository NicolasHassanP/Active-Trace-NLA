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
import { PageHeader, Card, CardContent, StatusBadge } from '@/shared/components/ui'

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
    <div data-testid="seguimiento-panel" className="space-y-6">
      {/* Header */}
      <PageHeader title="Seguimiento de alumnos" />

      {/* Counter card — shown once data is ready */}
      {!query.isLoading && !query.isError && (
        <Card>
          <CardContent>
            <div
              data-testid="seguimiento-counters"
              className="flex items-center gap-4 text-sm text-gray-600"
            >
              <span>
                <span className="font-semibold text-gray-900">{totalAlumnos}</span>{' '}
                {totalAlumnos === 1 ? 'alumno' : 'alumnos'}
              </span>
              {totalAtrasados > 0 && (
                <StatusBadge
                  status="atrasado"
                  label={`${totalAtrasados} atrasado${totalAtrasados !== 1 ? 's' : ''}`}
                />
              )}
            </div>
          </CardContent>
        </Card>
      )}

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
