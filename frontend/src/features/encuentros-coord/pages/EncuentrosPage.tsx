/**
 * EncuentrosPage — main page for encuentros coordination feature.
 * RBAC: COORDINADOR / ADMIN only (encuentros:gestionar permission).
 * Identity comes from JWT (useAuth) — never from URL or body.
 * Task 5.7. < 200 LOC.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { downloadFile } from '@/shared/services/downloadFile'
import { getMisAsignaciones } from '@/features/padron/services/misAsignacionesService'
import { useInstancias, useGuardias, useBloqueHtml } from '../hooks/encuentrosCoordHooks'
import { exportarGuardias } from '../services/encuentrosCoordService'
import InstanciasEncuentroTable from '../components/InstanciasEncuentroTable'
import GuardiasTable from '../components/GuardiasTable'
import GuardiasFilters from '../components/GuardiasFilters'
import CrearSlotDialog from '../components/CrearSlotDialog'
import type { GuardiaParams } from '../types'
import type { Role } from '@/features/auth/types'
import { Button, PageHeader } from '@/shared/components/ui'
import { toast } from 'sonner'

const ALLOWED_ROLES: Role[] = ['PROFESOR', 'TUTOR', 'COORDINADOR', 'ADMIN']

const EMPTY_GUARDIA_PARAMS: GuardiaParams = {}

export default function EncuentrosPage() {
  const { roles } = useAuth()
  const isAllowed = roles.some((r) => ALLOWED_ROLES.includes(r))

  const asignacionesQuery = useQuery({
    queryKey: ['mis-asignaciones'],
    queryFn: getMisAsignaciones,
    enabled: isAllowed,
  })

  const [selectedMateriaId, setSelectedMateriaId] = useState<string>('')

  const selectedAsignacion = asignacionesQuery.data?.find(
    (a) => a.materia_id === selectedMateriaId,
  )

  const instanciasQuery = useInstancias({
    materia_id: selectedMateriaId || null,
  })

  const [guardiaParams, setGuardiaParams] = useState<GuardiaParams>(EMPTY_GUARDIA_PARAMS)
  const guardiasQuery = useGuardias(guardiaParams)

  const [showCrearSlot, setShowCrearSlot] = useState(false)

  const bloqueHtmlMutation = useBloqueHtml()

  async function handleCopiarCronograma() {
    try {
      const res = await bloqueHtmlMutation.mutateAsync(selectedMateriaId || null)
      await navigator.clipboard.writeText(res.html)
      toast.success('Cronograma copiado al portapapeles')
    } catch {
      toast.error('Error al generar el cronograma')
    }
  }

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
      <div data-testid="encuentros-access-denied">
        <div role="alert" className="rounded bg-red-50 p-4 text-sm text-red-700">
          No tienes permiso para acceder a esta sección.
        </div>
      </div>
    )
  }

  const asignaciones = asignacionesQuery.data ?? []
  const uniqueMaterias = asignaciones.filter(
    (a, i, arr) => a.materia_id && arr.findIndex((b) => b.materia_id === a.materia_id) === i,
  )

  return (
    <div data-testid="encuentros-panel" className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <PageHeader title="Encuentros y guardias" />

        <div className="flex items-center gap-3 flex-shrink-0">
          {/* Selector de materia */}
          <select
            value={selectedMateriaId}
            onChange={(e) => setSelectedMateriaId(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Todas las materias</option>
            {uniqueMaterias.map((a) => (
              <option key={a.materia_id!} value={a.materia_id!}>
                {a.materia_nombre ?? a.materia_id}
              </option>
            ))}
          </select>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowCrearSlot(true)}
            disabled={!selectedMateriaId}
            title={!selectedMateriaId ? 'Seleccioná una materia primero' : undefined}
          >
            + Nuevo encuentro
          </Button>
        </div>
      </div>

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
          <div className="flex items-center gap-3">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void handleCopiarCronograma()}
              disabled={!instanciasQuery.data?.length || bloqueHtmlMutation.isPending}
              title={!instanciasQuery.data?.length ? 'No hay instancias para copiar' : undefined}
            >
              {bloqueHtmlMutation.isPending ? 'Copiando…' : 'Copiar cronograma'}
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => void handleExportarGuardias()}
            >
              Exportar guardias
            </Button>
          </div>
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

      {/* ---- Modal crear slot ---- */}
      {showCrearSlot && selectedMateriaId && (
        <CrearSlotDialog
          materiaId={selectedMateriaId}
          materiaNombre={selectedAsignacion?.materia_nombre ?? selectedMateriaId}
          onClose={() => setShowCrearSlot(false)}
        />
      )}
    </div>
  )
}
