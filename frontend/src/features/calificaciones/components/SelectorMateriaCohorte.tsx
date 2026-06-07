/**
 * SelectorMateriaCohorte — dropdown cargado desde /perfil/mis-asignaciones.
 * Reemplaza inputs de texto libre para evitar errores de UUID.
 */
import { useQuery } from '@tanstack/react-query'
import { getMisAsignaciones } from '@/features/padron/services/misAsignacionesService'

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
  const { data: asignaciones, isLoading, isError } = useQuery({
    queryKey: ['mis-asignaciones'],
    queryFn: getMisAsignaciones,
  })

  const selectedKey = materiaId && cohorteId ? `${materiaId}|${cohorteId}` : ''

  function handleChange(value: string) {
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
          onChange={(e) => handleChange(e.target.value)}
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
