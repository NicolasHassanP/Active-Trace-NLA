import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useTodasMaterias, useTodosCohortes } from '@/features/monitores/hooks/monitoresHooks'
import PadronImportForm from '../components/PadronImportForm'
import SyncMoodlePanel from '../components/SyncMoodlePanel'
import VaciarPadronButton from '../components/VaciarPadronButton'
import { PageHeader } from '@/shared/components/ui'
import { getMisAsignaciones } from '../services/misAsignacionesService'
import type { Role } from '@/features/auth/types'

const GLOBAL_ROLES: Role[] = ['ADMIN']

export default function PadronPage() {
  const { roles } = useAuth()
  const isGlobalScope = roles.some((r) => GLOBAL_ROLES.includes(r))

  const [selectedKey, setSelectedKey] = useState('')
  const [selectedMateriaId, setSelectedMateriaId] = useState('')
  const [selectedCohorteId, setSelectedCohorteId] = useState('')
  const [courseId, setCourseId] = useState('')

  const { data: asignaciones = [], isLoading: loadingAsignaciones } = useQuery({
    queryKey: ['mis-asignaciones'],
    queryFn: getMisAsignaciones,
    select: (rows) => {
      const seen = new Set<string>()
      return rows.filter((a) => {
        if (!a.materia_id || !a.cohorte_id) return false
        const key = `${a.materia_id}__${a.cohorte_id}`
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
    },
    enabled: !isGlobalScope,
  })

  const { data: todasMaterias = [], isLoading: loadingMaterias } = useTodasMaterias(isGlobalScope)
  const { data: todosCohortes = [], isLoading: loadingCohortes } = useTodosCohortes(isGlobalScope)

  const loadingSelector = isGlobalScope ? loadingMaterias || loadingCohortes : loadingAsignaciones

  const selected = asignaciones.find(
    (a) => `${a.materia_id}__${a.cohorte_id}` === selectedKey,
  )

  const materiaId = isGlobalScope ? selectedMateriaId : (selected?.materia_id ?? '')
  const cohorteId = isGlobalScope ? selectedCohorteId : (selected?.cohorte_id ?? '')
  const hasContext = Boolean(materiaId && cohorteId)

  return (
    <div className="space-y-8">
      <PageHeader title="Importación de Padrón" />

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-gray-700">Materia y Cohorte</h2>

        {loadingSelector ? (
          <p className="text-sm text-gray-500">Cargando materias…</p>
        ) : isGlobalScope ? (
          <div className="space-y-3">
            {todasMaterias.length === 0 ? (
              <p className="text-sm text-red-600">No hay materias registradas en el tenant.</p>
            ) : (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Seleccioná una materia
                </label>
                <select
                  value={selectedMateriaId}
                  onChange={(e) => {
                    setSelectedMateriaId(e.target.value)
                    setSelectedCohorteId('')
                  }}
                  className="w-full max-w-lg border rounded px-3 py-2 text-sm bg-white"
                  data-testid="materia-select"
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

            {selectedMateriaId && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Seleccioná una cohorte
                </label>
                {todosCohortes.length === 0 ? (
                  <p className="text-sm text-red-600">No hay cohortes registradas en el tenant.</p>
                ) : (
                  <select
                    value={selectedCohorteId}
                    onChange={(e) => setSelectedCohorteId(e.target.value)}
                    className="w-full max-w-lg border rounded px-3 py-2 text-sm bg-white"
                    data-testid="cohorte-select"
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
          </div>
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

      {!hasContext && !loadingSelector && (asignaciones.length > 0 || isGlobalScope) && (
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
