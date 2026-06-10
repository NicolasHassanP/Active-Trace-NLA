/**
 * GuardiasPage — "Registro de guardias".
 *
 * Combines the registration form (RegistrarGuardiaForm), the filtered list
 * (GuardiasTable) and a CSV export button.
 *
 * Source for the (materia, carrera, cohorte) selector: GET /equipos/mis-equipos
 * (useMisEquipos) — the only wired front-end source that exposes the full tripleta
 * (materia_id + carrera_id + cohorte_id) plus human-readable names. mis-asignaciones
 * was rejected because it does not expose carrera_id.
 *
 * Identity/tenant never sent from the client — resolved from the JWT on the backend.
 * Access: TUTOR / PROFESOR / COORDINADOR / ADMIN (encuentros:gestionar). < 200 LOC.
 */
import { useState } from 'react'
import { toast } from 'sonner'
import { PageHeader, Button } from '@/shared/components/ui'
import type { DomainError } from '@/shared/services/domainError'
import { downloadFile } from '@/shared/services/downloadFile'
import { useMisEquipos } from '@/features/equipos/hooks/equiposHooks'
import { useGuardias, useRegistrarGuardia } from '../hooks/guardiaHooks'
import { exportarGuardias } from '../services/guardiaService'
import RegistrarGuardiaForm from '../components/RegistrarGuardiaForm'
import GuardiasTable from '../components/GuardiasTable'
import type { GuardiaFiltros, RegistrarGuardiaRequest } from '../types'

const EMPTY_FILTROS: GuardiaFiltros = {}

function errorMessage(err: unknown): string {
  const e = err as Partial<DomainError>
  return e?.detail ?? 'No se pudo registrar la guardia'
}

export default function GuardiasPage() {
  const misEquiposQuery = useMisEquipos()
  const [filtros, setFiltros] = useState<GuardiaFiltros>(EMPTY_FILTROS)
  const guardiasQuery = useGuardias(filtros)
  const registrarMutation = useRegistrarGuardia()

  function handleRegistrar(body: RegistrarGuardiaRequest) {
    registrarMutation.mutate(body, {
      onSuccess: () => toast.success('Guardia registrada'),
      onError: (err) => toast.error(errorMessage(err)),
    })
  }

  async function handleExportar() {
    try {
      const blob = await exportarGuardias(filtros)
      downloadFile(blob, 'guardias.csv')
    } catch (err) {
      toast.error(errorMessage(err))
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Registro de guardias"
        subtitle="Registrá tus guardias de atención y consultá las existentes."
      />

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-gray-800">Nueva guardia</h2>
        <RegistrarGuardiaForm
          asignaciones={misEquiposQuery.data ?? []}
          onSubmit={handleRegistrar}
          isSubmitting={registrarMutation.isPending}
        />
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">Guardias registradas</h2>
          <Button variant="primary" size="sm" onClick={() => void handleExportar()}>
            Exportar CSV
          </Button>
        </div>

        {guardiasQuery.isLoading && <p className="text-sm text-gray-500">Cargando guardias…</p>}

        {guardiasQuery.isError && (
          <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
            No se pudieron cargar las guardias. Intentá nuevamente.
          </div>
        )}

        {!guardiasQuery.isLoading && !guardiasQuery.isError && (
          <GuardiasTable
            guardias={guardiasQuery.data ?? []}
            onFilter={(f) => setFiltros(f)}
            onClear={() => setFiltros(EMPTY_FILTROS)}
          />
        )}
      </section>
    </div>
  )
}
