/**
 * ColoquiosPage — main page for coloquios management feature.
 * RBAC: COORDINADOR / ADMIN only (coloquios:gestionar permission).
 * Identity comes from JWT (useAuth) — never from URL or body.
 * Task 6.11. < 200 LOC.
 */
import { useState } from 'react'
import { useAuth } from '@/features/auth/hooks/useAuth'
import {
  useMetricas,
  useConvocatorias,
  useCerrarConvocatoria,
} from '../hooks/coloquiosHooks'
import MetricasPanel from '../components/MetricasPanel'
import ConvocatoriasTable from '../components/ConvocatoriasTable'
import ConvocatoriaForm from '../components/ConvocatoriaForm'
import ImportarCandidatosDialog from '../components/ImportarCandidatosDialog'
import type { Role } from '@/features/auth/types'
import type { ConvocatoriaFormValues } from '../services/convocatoriaSchema'
import { crearConvocatoria } from '../services/coloquiosService'
import type { CrearConvocatoriaRequest } from '../types'
import { Button, PageHeader } from '@/shared/components/ui'

const ALLOWED_ROLES: Role[] = ['COORDINADOR', 'ADMIN']

export default function ColoquiosPage() {
  const { roles } = useAuth()
  const isAllowed = roles.some((r) => ALLOWED_ROLES.includes(r))

  const metricasQuery = useMetricas()
  const convocatoriasQuery = useConvocatorias()
  const cerrarMutation = useCerrarConvocatoria()

  const [showForm, setShowForm] = useState(false)
  const [importarId, setImportarId] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)

  async function handleCrearConvocatoria(values: ConvocatoriaFormValues) {
    setIsCreating(true)
    try {
      const body: CrearConvocatoriaRequest = {
        materia_id: values.materia_id,
        cohorte_id: values.cohorte_id,
        tipo: values.tipo,
        instancia: values.instancia,
        dias_disponibles: values.dias_disponibles,
        turnos: values.turnos.map((t) => ({
          fecha: t.fecha,
          cupo_total: t.cupo_total,
          franja: t.franja ?? null,
        })),
      }
      await crearConvocatoria(body)
      setShowForm(false)
    } finally {
      setIsCreating(false)
    }
  }

  function handleCerrar(id: string) {
    cerrarMutation.mutate(id)
  }

  if (!isAllowed) {
    return (
      <div data-testid="coloquios-access-denied" className="max-w-6xl mx-auto p-6">
        <div role="alert" className="rounded bg-red-50 p-4 text-sm text-red-700">
          Acceso denegado. Esta sección es exclusiva para Coordinadores y Administradores.
        </div>
      </div>
    )
  }

  return (
    <div data-testid="coloquios-panel" className="max-w-6xl mx-auto space-y-8 p-6">
      <PageHeader title="Coloquios" />

      {/* ---- Métricas ---- */}
      {metricasQuery.isLoading && (
        <p className="text-sm text-gray-500">Cargando métricas…</p>
      )}
      {metricasQuery.isError && (
        <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
          Error al cargar las métricas.
        </div>
      )}
      {metricasQuery.data && <MetricasPanel metricas={metricasQuery.data} />}

      {/* ---- Convocatorias ---- */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">Convocatorias</h2>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowForm((v) => !v)}
          >
            Nueva convocatoria
          </Button>
        </div>

        {showForm && (
          <div className="rounded border border-gray-200 bg-gray-50 p-4">
            <ConvocatoriaForm
              onSubmit={(values) => void handleCrearConvocatoria(values)}
              isLoading={isCreating}
            />
          </div>
        )}

        {convocatoriasQuery.isLoading && (
          <p className="text-sm text-gray-500">Cargando convocatorias…</p>
        )}
        {convocatoriasQuery.isError && (
          <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
            Error al cargar las convocatorias.
          </div>
        )}
        {!convocatoriasQuery.isLoading && !convocatoriasQuery.isError && (
          <ConvocatoriasTable
            convocatorias={convocatoriasQuery.data ?? []}
            onImportar={(id) => setImportarId(id)}
            onCerrar={handleCerrar}
            onVerResultados={() => {/* navigate to results — batch 4 routing */}}
          />
        )}
      </section>

      {/* ---- Importar candidatos dialog ---- */}
      {importarId && (
        <ImportarCandidatosDialog
          evaluacionId={importarId}
          onClose={() => setImportarId(null)}
          onSuccess={() => setImportarId(null)}
        />
      )}
    </div>
  )
}
