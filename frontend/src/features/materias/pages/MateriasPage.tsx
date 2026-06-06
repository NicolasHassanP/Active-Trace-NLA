/**
 * MateriasPage — F4.2 Vista de mis equipos.
 * Shows the authenticated user's materia assignments (materia × carrera × cohorte × rol × vigencia).
 * Identity comes from JWT (no URL params, no body identity).
 * < 200 LOC.
 */
import { useMisMaterias } from '../hooks/materiasHooks'
import MisMateriasTable from '../components/MisMateriasTable'

export default function MateriasPage() {
  const { data, isLoading, isError } = useMisMaterias()

  const items = data ?? []

  return (
    <div className="max-w-6xl mx-auto space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Mis materias</h1>
        <p className="mt-1 text-sm text-gray-500">
          Tus asignaciones como docente: materia, carrera, cohorte, rol y vigencia.
        </p>
      </div>

      {isLoading && (
        <p className="text-sm text-gray-500">Cargando asignaciones…</p>
      )}

      {isError && (
        <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
          Error al cargar las asignaciones. Intentá recargar la página.
        </div>
      )}

      {!isLoading && !isError && (
        <MisMateriasTable items={items} />
      )}
    </div>
  )
}
