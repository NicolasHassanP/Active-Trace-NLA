/**
 * PadronPage — composes materia/cohorte selector + import + sync + empty.
 * Materia/cohorte se cargan desde GET /perfil/mis-asignaciones (C-25 fix).
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import PadronImportForm from '../components/PadronImportForm'
import SyncMoodlePanel from '../components/SyncMoodlePanel'
import VaciarPadronButton from '../components/VaciarPadronButton'
import { PageHeader } from '@/shared/components/ui'
import { getMisAsignaciones } from '../services/misAsignacionesService'

export default function PadronPage() {
  const [selectedKey, setSelectedKey] = useState('')
  const [courseId, setCourseId] = useState('')

  const { data: asignaciones = [], isLoading } = useQuery({
    queryKey: ['mis-asignaciones'],
    queryFn: getMisAsignaciones,
    select: (rows) => rows.filter((a) => a.materia_id && a.cohorte_id),
  })

  const selected = asignaciones.find(
    (a) => `${a.materia_id}__${a.cohorte_id}` === selectedKey,
  )
  const materiaId = selected?.materia_id ?? ''
  const cohorteId = selected?.cohorte_id ?? ''
  const hasContext = Boolean(materiaId && cohorteId)

  return (
    <div className="space-y-8">
      <PageHeader title="Importación de Padrón" />

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-gray-700">Materia y Cohorte</h2>

        {isLoading ? (
          <p className="text-sm text-gray-500">Cargando materias…</p>
        ) : asignaciones.length === 0 ? (
          <p className="text-sm text-red-600">
            No tenés materias asignadas con cohorte. Contactá al coordinador.
          </p>
        ) : (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Seleccionar materia y cohorte
            </label>
            <select
              value={selectedKey}
              onChange={(e) => setSelectedKey(e.target.value)}
              className="w-full max-w-lg border rounded px-3 py-2 text-sm bg-white"
              data-testid="materia-cohorte-select"
            >
              <option value="">— Seleccioná una materia —</option>
              {asignaciones.map((a) => {
                const key = `${a.materia_id}__${a.cohorte_id}`
                const label = `${a.materia_nombre ?? a.materia_id} · ${a.cohorte_nombre ?? a.cohorte_id}`
                return (
                  <option key={key} value={key}>
                    {label}
                  </option>
                )
              })}
            </select>
          </div>
        )}
      </section>

      {!hasContext && !isLoading && asignaciones.length > 0 && (
        <p className="text-sm text-gray-500 italic">
          Seleccioná una materia y cohorte para continuar.
        </p>
      )}

      {hasContext && (
        <>
          <section className="space-y-3 border-t pt-6">
            <h2 className="text-lg font-semibold text-gray-700">Importar archivo</h2>
            <PadronImportForm materia_id={materiaId} cohorte_id={cohorteId} />
          </section>

          <section className="space-y-3 border-t pt-6">
            <h2 className="text-lg font-semibold text-gray-700">Sincronizar desde Moodle</h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Course ID de Moodle
              </label>
              <input
                type="text"
                value={courseId}
                onChange={(e) => setCourseId(e.target.value)}
                placeholder="ej. 42"
                className="w-full max-w-xs border rounded px-3 py-2 text-sm"
                data-testid="course-id-input"
              />
            </div>
            {courseId && (
              <SyncMoodlePanel
                materia_id={materiaId}
                cohorte_id={cohorteId}
                course_id={courseId}
              />
            )}
          </section>

          <section className="space-y-3 border-t pt-6">
            <h2 className="text-lg font-semibold text-gray-700">Gestión del padrón activo</h2>
            <VaciarPadronButton materia_id={materiaId} cohorte_id={cohorteId} />
          </section>
        </>
      )}
    </div>
  )
}
