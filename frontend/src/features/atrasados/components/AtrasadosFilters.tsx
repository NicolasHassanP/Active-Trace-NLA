/**
 * AtrasadosFilters — multi-select for activity filter.
 * The available activities are inferred from the loaded data. < 200 LOC.
 */
import type { AlumnoAtrasado } from '../types'

interface Props {
  alumnos: AlumnoAtrasado[]
  selectedActividades: string[]
  onChangeActividades: (acts: string[]) => void
}

export default function AtrasadosFilters({
  alumnos,
  selectedActividades,
  onChangeActividades,
}: Props) {
  // Infer all unique activity names from the loaded data
  const allActividades = Array.from(
    new Set(alumnos.flatMap((a) => [...a.actividades_faltantes, ...a.actividades_no_aprobadas])),
  ).sort()

  if (allActividades.length === 0) return null

  function toggleActividad(act: string) {
    if (selectedActividades.includes(act)) {
      onChangeActividades(selectedActividades.filter((a) => a !== act))
    } else {
      onChangeActividades([...selectedActividades, act])
    }
  }

  return (
    <div className="space-y-2" data-testid="atrasados-filters">
      <p className="text-sm font-medium text-gray-700">Filtrar por actividad:</p>
      <div className="flex flex-wrap gap-2">
        {allActividades.map((act) => (
          <label key={act} className="flex items-center gap-1 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={selectedActividades.includes(act)}
              onChange={() => toggleActividad(act)}
            />
            {act}
          </label>
        ))}
      </div>
    </div>
  )
}
