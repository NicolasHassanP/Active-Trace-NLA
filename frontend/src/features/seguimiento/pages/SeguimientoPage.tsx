/**
 * SeguimientoPage — F2.8 Monitor de seguimiento (TUTOR / PROFESOR view).
 *
 * RBAC: TUTOR, PROFESOR, COORDINADOR, ADMIN.
 * Identity always from JWT (useAuth) — never from URL params or body.
 * Backend auto-scopes: PROFESOR/TUTOR → only their students; COORD/ADMIN → all.
 *
 * Requires a materia+cohorte selection before loading data (same pattern as
 * AtrasadosPage). Shows a dropdown loaded from GET /perfil/mis-asignaciones.
 * When no selection, shows a prompt instead of an empty table.
 *
 * Header counters: total alumnos + Y atrasados.
 * Filters: búsqueda (debounce 300ms), comisión, regional, min_cumplidas (immediate).
 *
 * < 200 LOC. No `any`. Only Tailwind.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSeguimiento } from '../hooks/seguimientoHooks'
import SeguimientoFiltros from '../components/SeguimientoFiltros'
import SeguimientoTable from '../components/SeguimientoTable'
import type { SeguimientoParams } from '../types'
import { PageHeader, Card, CardContent, StatusBadge } from '@/shared/components/ui'
import { getMisAsignaciones } from '@/features/padron/services/misAsignacionesService'

export default function SeguimientoPage() {
  const [selectedKey, setSelectedKey] = useState('')
  const [filterParams, setFilterParams] = useState<Omit<SeguimientoParams, 'materia_id' | 'cohorte_id'>>({})

  const { data: asignaciones = [], isLoading: loadingAsignaciones } = useQuery({
    queryKey: ['mis-asignaciones'],
    queryFn: getMisAsignaciones,
    select: (rows) => rows.filter((a) => a.materia_id && a.cohorte_id),
  })

  const selectedAsignacion = asignaciones.find(
    (a) => `${a.materia_id}__${a.cohorte_id}` === selectedKey,
  )

  const materiaId = selectedAsignacion?.materia_id ?? ''
  const cohorteId = selectedAsignacion?.cohorte_id ?? ''

  const params: SeguimientoParams = {
    materia_id: materiaId || null,
    cohorte_id: cohorteId || null,
    ...filterParams,
  }

  const query = useSeguimiento(params)

  const filas = query.data ?? []
  const totalAlumnos = filas.length
  const totalAtrasados = filas.filter((f) => f.estado === 'atrasado').length

  function handleFilter(newParams: SeguimientoParams) {
    const { materia_id: _m, cohorte_id: _c, ...rest } = newParams
    setFilterParams(rest)
  }

  function handleClear() {
    setFilterParams({})
  }

  return (
    <div data-testid="seguimiento-panel" className="space-y-6">
      {/* Header */}
      <PageHeader title="Seguimiento de alumnos" />

      {/* Materia y Cohorte selector */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-gray-700">Materia y Cohorte</h2>

        {loadingAsignaciones ? (
          <p className="text-sm text-gray-500">Cargando materias…</p>
        ) : asignaciones.length === 0 ? (
          <p className="text-sm text-red-600">
            No tenés materias asignadas con cohorte. Contactá al coordinador.
          </p>
        ) : (
          <select
            value={selectedKey}
            onChange={(e) => {
              setSelectedKey(e.target.value)
              setFilterParams({})
            }}
            className="w-full max-w-lg border rounded px-3 py-2 text-sm bg-white"
            data-testid="selector-asignacion"
          >
            <option value="">— Seleccioná una materia —</option>
            {asignaciones.map((a) => {
              const key = `${a.materia_id}__${a.cohorte_id}`
              return (
                <option key={key} value={key}>
                  {a.materia_nombre ?? a.materia_id} · {a.cohorte_nombre ?? a.cohorte_id}
                </option>
              )
            })}
          </select>
        )}
      </section>

      {/* No selection prompt */}
      {!materiaId && !loadingAsignaciones && (
        <p className="text-sm text-gray-500 italic">
          Seleccioná una materia y cohorte para ver el seguimiento.
        </p>
      )}

      {/* Content — only shown when materia+cohorte are selected */}
      {materiaId && cohorteId && (
        <>
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
        </>
      )}
    </div>
  )
}
