/**
 * EncuentrosPage — main page for encuentros coordination feature.
 * RBAC: COORDINADOR / ADMIN only (encuentros:gestionar permission).
 * Identity comes from JWT (useAuth) — never from URL or body.
 * Task 5.7. < 200 LOC.
 */
import { useState } from 'react'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { downloadFile } from '@/shared/services/downloadFile'
import { useInstancias, useGuardias } from '../hooks/encuentrosCoordHooks'
import { exportarGuardias } from '../services/encuentrosCoordService'
import InstanciasEncuentroTable from '../components/InstanciasEncuentroTable'
import GuardiasTable from '../components/GuardiasTable'
import GuardiasFilters from '../components/GuardiasFilters'
import type { GuardiaParams } from '../types'
import type { Role } from '@/features/auth/types'

const ALLOWED_ROLES: Role[] = ['COORDINADOR', 'ADMIN']

const EMPTY_GUARDIA_PARAMS: GuardiaParams = {}

export default function EncuentrosPage() {
  const { roles } = useAuth()
  const isAllowed = roles.some((r) => ALLOWED_ROLES.includes(r))

  const instanciasQuery = useInstancias({})
  const [guardiaParams, setGuardiaParams] = useState<GuardiaParams>(EMPTY_GUARDIA_PARAMS)
  const guardiasQuery = useGuardias(guardiaParams)

  async function handleExportarGuardias() {
    try {
      const blob = await exportarGuardias(guardiaParams)
      downloadFile(blob, 'guardias.csv')
    } catch {
      // error handled silently — toast integration is a UI concern
    }
  }

  if (!isAllowed) {
    return (
      <div data-testid="encuentros-access-denied" className="max-w-6xl mx-auto p-6">
        <div role="alert" className="rounded bg-red-50 p-4 text-sm text-red-700">
          Acceso denegado. Esta sección es exclusiva para Coordinadores y Administradores.
        </div>
      </div>
    )
  }

  return (
    <div data-testid="encuentros-panel" className="max-w-6xl mx-auto space-y-8 p-6">
      <h1 className="text-2xl font-bold text-gray-900">Encuentros y guardias</h1>

      {/* ---- Instancias de encuentro ---- */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-gray-800">Instancias de encuentro</h2>

        {instanciasQuery.isLoading && (
          <p className="text-sm text-gray-500">Cargando instancias…</p>
        )}

        {instanciasQuery.isError && (
          <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
            Error al cargar las instancias de encuentro.
          </div>
        )}

        {!instanciasQuery.isLoading && !instanciasQuery.isError && (
          <InstanciasEncuentroTable instancias={instanciasQuery.data ?? []} />
        )}
      </section>

      {/* ---- Guardias ---- */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">Registro de guardias</h2>
          <button
            type="button"
            onClick={() => void handleExportarGuardias()}
            className="rounded bg-green-600 px-4 py-1.5 text-sm text-white hover:bg-green-700"
          >
            Exportar guardias
          </button>
        </div>

        <GuardiasFilters
          onFilter={(params) => setGuardiaParams(params)}
          onClear={() => setGuardiaParams(EMPTY_GUARDIA_PARAMS)}
        />

        {guardiasQuery.isLoading && (
          <p className="text-sm text-gray-500">Cargando guardias…</p>
        )}

        {guardiasQuery.isError && (
          <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
            Error al cargar las guardias.
          </div>
        )}

        {!guardiasQuery.isLoading && !guardiasQuery.isError && (
          <GuardiasTable guardias={guardiasQuery.data ?? []} />
        )}
      </section>
    </div>
  )
}
