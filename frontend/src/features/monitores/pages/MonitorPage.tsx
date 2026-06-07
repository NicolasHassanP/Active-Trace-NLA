/**
 * MonitorPage — main page for the Monitor general feature.
 * RBAC: COORDINADOR / ADMIN only.
 * Identity comes from JWT (useAuth) — never from URL or body.
 * materia_id / cohorte_id se seleccionan via dropdown (mis-asignaciones),
 * igual que SeguimientoPage y AtrasadosPage.
 * Task 4.6. < 200 LOC.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useMonitor } from '../hooks/monitoresHooks'
import MonitorFilters from '../components/MonitorFilters'
import MonitorTable from '../components/MonitorTable'
import MonitorToolbar from '../components/MonitorToolbar'
import type { MonitorParams } from '../types'
import type { Role } from '@/features/auth/types'
import { PageHeader } from '@/shared/components/ui'
import { getMisAsignaciones } from '@/features/padron/services/misAsignacionesService'

const ALLOWED_ROLES: Role[] = ['COORDINADOR', 'ADMIN']

export default function MonitorPage() {
  const { roles } = useAuth()
  const isAllowed = roles.some((r) => ALLOWED_ROLES.includes(r))

  const [selectedKey, setSelectedKey] = useState('')
  const [filterParams, setFilterParams] = useState<Omit<MonitorParams, 'materia_id' | 'cohorte_id'>>({})

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

  const params: MonitorParams = {
    materia_id: materiaId || null,
    cohorte_id: cohorteId || null,
    ...filterParams,
  }

  const monitorQuery = useMonitor(params)

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

      {/* Selector materia+cohorte */}
      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-gray-700">Materia y Cohorte</h2>
        {loadingAsignaciones ? (
          <p className="text-sm text-gray-500">Cargando materias…</p>
        ) : asignaciones.length === 0 ? (
          <p className="text-sm text-red-600">No tenés materias asignadas con cohorte.</p>
        ) : (
          <select
            value={selectedKey}
            onChange={(e) => {
              setSelectedKey(e.target.value)
              setFilterParams({})
            }}
            className="w-full max-w-lg border rounded px-3 py-2 text-sm bg-white"
            data-testid="monitor-selector-asignacion"
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

      {!materiaId && !loadingAsignaciones && (
        <p className="text-sm text-gray-500 italic">
          Seleccioná una materia y cohorte para ver el monitor.
        </p>
      )}

      {materiaId && cohorteId && (
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
