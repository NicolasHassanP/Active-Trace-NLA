/**
 * EquiposPage — main page for the Equipos feature.
 * RBAC: COORDINADOR/ADMIN see full management panel + mis-equipos.
 *       PROFESOR/TUTOR/NEXO see only mis-equipos (no management actions).
 * Identity comes from JWT (useAuth) — never from URL or body.
 * Task 1.9, 1.10. < 200 LOC.
 */
import { useState } from 'react'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useMisEquipos, useEquipo } from '../hooks/equiposHooks'
import { exportarEquipo } from '../services/equiposService'
import { downloadFile } from '@/shared/services/downloadFile'
import MisEquiposTable from '../components/MisEquiposTable'
import EquipoFilters from '../components/EquipoFilters'
import AsignacionMasivaForm from '../components/AsignacionMasivaForm'
import ClonarEquipoDialog from '../components/ClonarEquipoDialog'
import VigenciaGeneralForm from '../components/VigenciaGeneralForm'
import type { EquipoQueryParams } from '../types'
import type { Role } from '@/features/auth/types'
import { Button, PageHeader } from '@/shared/components/ui'

const MANAGEMENT_ROLES: Role[] = ['COORDINADOR', 'ADMIN']

export default function EquiposPage() {
  const { roles } = useAuth()
  const isManager = roles.some((r) => MANAGEMENT_ROLES.includes(r))

  const misEquiposQuery = useMisEquipos()
  const [equipoParams, setEquipoParams] = useState<EquipoQueryParams | null>(null)
  const equipoQuery = useEquipo(
    equipoParams ?? { materia_id: '', carrera_id: '', cohorte_id: '' },
  )

  const [exporting, setExporting] = useState(false)

  async function handleExport() {
    if (!equipoParams) return
    setExporting(true)
    try {
      const blob = await exportarEquipo(equipoParams)
      downloadFile(blob, 'equipo.csv')
    } finally {
      setExporting(false)
    }
  }

  const misItems = misEquiposQuery.data ?? []

  return (
    <div className="space-y-8">
      <PageHeader title="Equipos docentes" />

      {/* Mis equipos — visible for all authorized roles */}
      <section>
        <h2 className="text-lg font-semibold text-gray-700 mb-3">Mis asignaciones</h2>

        {misEquiposQuery.isLoading && (
          <p className="text-sm text-gray-500">Cargando asignaciones…</p>
        )}

        {misEquiposQuery.isError && (
          <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
            Error al cargar las asignaciones.
          </div>
        )}

        {!misEquiposQuery.isLoading && !misEquiposQuery.isError && (
          <MisEquiposTable items={misItems} />
        )}
      </section>

      {/* Management section — COORDINADOR / ADMIN only */}
      {isManager && (
        <section data-testid="equipos-gestion" className="space-y-8 border-t border-gray-200 pt-8">
          <div>
            <h2 className="text-lg font-semibold text-gray-700 mb-3">Consultar equipo</h2>
            <EquipoFilters onSearch={setEquipoParams} />

            {equipoParams && equipoQuery.data && equipoQuery.data.length > 0 && (
              <div className="mt-4">
                <MisEquiposTable items={equipoQuery.data} />
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleExport}
                  isLoading={exporting}
                  disabled={exporting}
                  className="mt-2"
                >
                  Exportar CSV
                </Button>
              </div>
            )}
          </div>

          <div>
            <AsignacionMasivaForm />
          </div>

          <div>
            <ClonarEquipoDialog />
          </div>

          <div>
            <VigenciaGeneralForm />
          </div>
        </section>
      )}
    </div>
  )
}
