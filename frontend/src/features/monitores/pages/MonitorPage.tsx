/**
 * MonitorPage — main page for the Monitor general feature.
 * RBAC: COORDINADOR / ADMIN only.
 * Identity comes from JWT (useAuth) — never from URL or body.
 * Task 4.6. < 200 LOC.
 */
import { useState } from 'react'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useMonitor } from '../hooks/monitoresHooks'
import MonitorFilters from '../components/MonitorFilters'
import MonitorTable from '../components/MonitorTable'
import MonitorToolbar from '../components/MonitorToolbar'
import type { MonitorParams } from '../types'
import type { Role } from '@/features/auth/types'
import { PageHeader } from '@/shared/components/ui'

const ALLOWED_ROLES: Role[] = ['COORDINADOR', 'ADMIN']

const EMPTY_PARAMS: MonitorParams = {}

export default function MonitorPage() {
  const { roles } = useAuth()
  const isAllowed = roles.some((r) => ALLOWED_ROLES.includes(r))

  const [params, setParams] = useState<MonitorParams>(EMPTY_PARAMS)
  const monitorQuery = useMonitor(params)

  function handleFilter(newParams: MonitorParams) {
    setParams(newParams)
  }

  function handleClear() {
    setParams(EMPTY_PARAMS)
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
    </div>
  )
}
