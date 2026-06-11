/**
 * MateriasPage — F4.2 Vista de mis equipos.
 * Shows the authenticated user's materia assignments (materia × carrera × cohorte × rol × vigencia).
 * Identity comes from JWT (no URL params, no body identity).
 * < 200 LOC.
 */
import { useMisMaterias } from '../hooks/materiasHooks'
import MisMateriasTable from '../components/MisMateriasTable'
import { PageHeader, EmptyState } from '@/shared/components/ui'

export default function MateriasPage() {
  const { data, isLoading, isError } = useMisMaterias()

  const items = data ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Mis materias"
        subtitle="Tus asignaciones como docente: materia, carrera, cohorte, rol y vigencia."
      />

      {isLoading && (
        <p className="text-sm text-gray-500">Cargando asignaciones…</p>
      )}

      {isError && (
        <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
          Error al cargar las asignaciones. Intentá recargar la página.
        </div>
      )}

      {!isLoading && !isError && items.length === 0 && (
        <EmptyState
          title="No tenés asignaciones actualmente."
          description="Cuando se te asigne una materia, aparecerá aquí."
        />
      )}

      {!isLoading && !isError && items.length > 0 && (
        <MisMateriasTable items={items} />
      )}
    </div>
  )
}
