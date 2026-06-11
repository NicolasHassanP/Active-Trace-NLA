import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useTodasMaterias, useTodosCohortes } from '@/features/monitores/hooks/monitoresHooks'
import { getMisAsignaciones } from '@/features/padron/services/misAsignacionesService'
import type { Role } from '@/features/auth/types'

const GLOBAL_ROLES: Role[] = ['ADMIN']

interface Props {
  materiaId: string
  cohorteId: string
  onMateriaChange: (v: string) => void
  onCohorteChange: (v: string) => void
}

export default function SelectorMateriaCohorte({
  materiaId,
  cohorteId,
  onMateriaChange,
  onCohorteChange,
}: Props) {
  const { roles } = useAuth()
  const isGlobalScope = roles.some((r) => GLOBAL_ROLES.includes(r))

  const { data: asignaciones, isLoading: loadingAsignaciones, isError } = useQuery({
    queryKey: ['mis-asignaciones'],
    queryFn: getMisAsignaciones,
    enabled: !isGlobalScope,
  })

  const { data: todasMaterias = [], isLoading: loadingMaterias } = useTodasMaterias(isGlobalScope)
  const { data: todosCohortes = [], isLoading: loadingCohortes } = useTodosCohortes(isGlobalScope)

  const isLoading = isGlobalScope ? loadingMaterias || loadingCohortes : loadingAsignaciones

  const selectedKey = materiaId && cohorteId ? `${materiaId}|${cohorteId}` : ''

  function handleAsignacionChange(value: string) {
    if (!value) {
      onMateriaChange('')
      onCohorteChange('')
      return
    }
    const [mid, cid] = value.split('|')
    onMateriaChange(mid)
    onCohorteChange(cid)
  }

  if (isLoading) {
    return <p className="text-sm text-gray-500 italic">Cargando asignaciones…</p>
  }

  if (isGlobalScope) {
    return (
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-gray-700">Materia y Cohorte</h2>

        {todasMaterias.length === 0 ? (
          <p className="text-sm text-red-600">No hay materias registradas en el tenant.</p>
        ) : (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Seleccioná una materia
            </label>
            <select
              value={materiaId}
              onChange={(e) => {
                onMateriaChange(e.target.value)
                onCohorteChange('')
              }}
              className="w-full border rounded px-3 py-2 text-sm bg-white"
              data-testid="selector-materia"
            >
              <option value="">— Seleccioná una materia —</option>
              {todasMaterias.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.nombre}
                </option>
              ))}
            </select>
          </div>
        )}

        {materiaId && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Seleccioná una cohorte
            </label>
            {todosCohortes.length === 0 ? (
              <p className="text-sm text-red-600">No hay cohortes registradas en el tenant.</p>
            ) : (
              <select
                value={cohorteId}
                onChange={(e) => onCohorteChange(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm bg-white"
                data-testid="selector-cohorte"
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
    )
  }

  if (isError || !asignaciones) {
    return <p className="text-sm text-red-500">Error al cargar asignaciones. Recargá la página.</p>
  }

  const options = asignaciones.filter((a) => a.materia_id && a.cohorte_id)

  if (options.length === 0) {
    return (
      <p className="text-sm text-gray-500 italic">
        No tenés materias asignadas con cohorte. Contactá al coordinador.
      </p>
    )
  }

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-gray-700">Materia y Cohorte</h2>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Seleccioná una asignación
        </label>
        <select
          value={selectedKey}
          onChange={(e) => handleAsignacionChange(e.target.value)}
          className="w-full border rounded px-3 py-2 text-sm"
          data-testid="selector-asignacion"
        >
          <option value="">— elegí materia y cohorte —</option>
          {options.map((a) => (
            <option key={`${a.materia_id}|${a.cohorte_id}`} value={`${a.materia_id}|${a.cohorte_id}`}>
              {a.materia_nombre ?? a.materia_id} · {a.cohorte_nombre ?? a.cohorte_id}
            </option>
          ))}
        </select>
      </div>
    </section>
  )
}
