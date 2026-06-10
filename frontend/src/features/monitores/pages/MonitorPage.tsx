import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useMonitor, useTodasMaterias, useTodosCohortes } from '../hooks/monitoresHooks'
import MonitorFilters from '../components/MonitorFilters'
import MonitorTable from '../components/MonitorTable'
import MonitorToolbar from '../components/MonitorToolbar'
import type { MonitorParams } from '../types'
import type { Role } from '@/features/auth/types'
import { PageHeader } from '@/shared/components/ui'
import { getMisAsignaciones } from '@/features/padron/services/misAsignacionesService'

const GLOBAL_ROLES: Role[] = ['ADMIN']
const ALLOWED_ROLES: Role[] = ['COORDINADOR', 'ADMIN']

export default function MonitorPage() {
  const { roles } = useAuth()
  const isGlobalScope = roles.some((r) => GLOBAL_ROLES.includes(r))
  const isAllowed = roles.some((r) => ALLOWED_ROLES.includes(r))

  const [selectedMateriaId, setSelectedMateriaId] = useState('')
  const [selectedCohorteId, setSelectedCohorteId] = useState('')
  const [filterParams, setFilterParams] = useState<Omit<MonitorParams, 'materia_id' | 'cohorte_id'>>({})

  const { data: asignaciones = [], isLoading: loadingAsignaciones } = useQuery({
    queryKey: ['mis-asignaciones'],
    queryFn: getMisAsignaciones,
    select: (rows) => rows.filter((a) => a.materia_id && a.cohorte_id),
    enabled: !isGlobalScope,
  })

  const { data: todasMaterias = [], isLoading: loadingMaterias } = useTodasMaterias(isGlobalScope)
  const { data: todosCohortes = [], isLoading: loadingCohortes } = useTodosCohortes(isGlobalScope)

  const loadingSelector = isGlobalScope ? loadingMaterias || loadingCohortes : loadingAsignaciones

  function resolveParams(): MonitorParams {
    if (isGlobalScope) {
      return {
        materia_id: selectedMateriaId || null,
        cohorte_id: selectedCohorteId || null,
        ...filterParams,
      }
    }
    const found = asignaciones.find(
      (a) => `${a.materia_id}` === selectedMateriaId,
    )
    return {
      materia_id: found?.materia_id ?? null,
      cohorte_id: found?.cohorte_id ?? null,
      ...filterParams,
    }
  }

  const params = resolveParams()
  const hasSelection = isGlobalScope
    ? Boolean(selectedMateriaId && selectedCohorteId)
    : Boolean(params.materia_id && params.cohorte_id)
  const monitorQuery = useMonitor(params, hasSelection)

  function handleFilter(newParams: MonitorParams) {
    const { materia_id: _m, cohorte_id: _c, ...rest } = newParams
    setFilterParams(rest)
  }

  function handleClear() {
    setFilterParams({})
  }

  if (!isAllowed) {
    return (
      <div data-testid="monitor-access-denied">
        <div role="alert" className="rounded bg-red-50 p-4 text-sm text-red-700">
          Acceso denegado. Esta sección es exclusiva para Coordinadores y Administradores.
        </div>
      </div>
    )
  }

  return (
    <div data-testid="monitor-panel" className="space-y-6">
      <PageHeader title="Monitor general de actividades" />

      <section className="space-y-4">
        <div className="space-y-2">
          <h2 className="text-lg font-semibold text-gray-700">Materia</h2>
          {loadingSelector ? (
            <p className="text-sm text-gray-500">Cargando opciones…</p>
          ) : isGlobalScope ? (
            todasMaterias.length === 0 ? (
              <p className="text-sm text-red-600">No hay materias registradas en el tenant.</p>
            ) : (
              <select
                value={selectedMateriaId}
                onChange={(e) => {
                  setSelectedMateriaId(e.target.value)
                  setSelectedCohorteId('')
                  setFilterParams({})
                }}
                className="w-full max-w-lg border rounded px-3 py-2 text-sm bg-white"
                data-testid="monitor-selector-asignacion"
              >
                <option value="">— Seleccioná una materia —</option>
                {todasMaterias.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.nombre}
                  </option>
                ))}
              </select>
            )
          ) : asignaciones.length === 0 ? (
            <p className="text-sm text-red-600">No tenés materias asignadas con cohorte.</p>
          ) : (
            <select
              value={selectedMateriaId}
              onChange={(e) => {
                setSelectedMateriaId(e.target.value)
                setFilterParams({})
              }}
              className="w-full max-w-lg border rounded px-3 py-2 text-sm bg-white"
              data-testid="monitor-selector-asignacion"
            >
              <option value="">— Seleccioná una materia —</option>
              {asignaciones.map((a) => {
                const key = `${a.materia_id}`
                return (
                  <option key={key} value={key}>
                    {a.materia_nombre ?? a.materia_id} · {a.cohorte_nombre ?? a.cohorte_id}
                  </option>
                )
              })}
            </select>
          )}
        </div>

        {isGlobalScope && selectedMateriaId && (
          <div className="space-y-2">
            <h2 className="text-lg font-semibold text-gray-700">Cohorte</h2>
            {todosCohortes.length === 0 ? (
              <p className="text-sm text-red-600">No hay cohortes registradas en el tenant.</p>
            ) : (
              <select
                value={selectedCohorteId}
                onChange={(e) => {
                  setSelectedCohorteId(e.target.value)
                  setFilterParams({})
                }}
                className="w-full max-w-lg border rounded px-3 py-2 text-sm bg-white"
                data-testid="monitor-selector-cohorte"
              >
                <option value="">— Seleccioná una cohorte —</option>
                {todosCohortes.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre} ({c.anio})
                  </option>
                ))}
              </select>
            )}
          </div>
        )}
      </section>

      {!hasSelection && !loadingSelector && (
        <p className="text-sm text-gray-500 italic">
          {isGlobalScope && selectedMateriaId
            ? 'Seleccioná una cohorte para ver el monitor.'
            : 'Seleccioná una materia para ver el monitor.'}
        </p>
      )}

      {hasSelection && (
        <>
          <MonitorFilters onFilter={handleFilter} onClear={handleClear} />

          <MonitorToolbar
            filas={monitorQuery.data ?? []}
            onClear={handleClear}
          />

          {monitorQuery.isLoading && (
            <p className="text-sm text-gray-500">Cargando monitor…</p>
          )}

          {monitorQuery.isError && (
            <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
              Error al cargar el monitor.
            </div>
          )}

          {!monitorQuery.isLoading && !monitorQuery.isError && (
            <MonitorTable filas={monitorQuery.data ?? []} />
          )}
        </>
      )}
    </div>
  )
}
