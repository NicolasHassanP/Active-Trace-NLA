/**
 * PadronPage — composes materia/cohorte selector + import + sync + empty.
 * Materia/cohorte are stored in local state (catalog is out of scope for C-22).
 */
import { useState } from 'react'
import PadronImportForm from '../components/PadronImportForm'
import SyncMoodlePanel from '../components/SyncMoodlePanel'
import VaciarPadronButton from '../components/VaciarPadronButton'
import { PageHeader } from '@/shared/components/ui'

export default function PadronPage() {
  const [materiaId, setMateriaId] = useState('')
  const [cohorteId, setCohorteId] = useState('')
  const [courseId, setCourseId] = useState('')

  const hasContext = materiaId.trim() !== '' && cohorteId.trim() !== ''

  return (
    <div className="space-y-8">
      <PageHeader title="Importación de Padrón" />

      {/* Selector de contexto */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-gray-700">Materia y Cohorte</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              ID de Materia
            </label>
            <input
              type="text"
              value={materiaId}
              onChange={(e) => setMateriaId(e.target.value)}
              placeholder="ej. m-001"
              className="w-full border rounded px-3 py-2 text-sm"
              data-testid="materia-id-input"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              ID de Cohorte
            </label>
            <input
              type="text"
              value={cohorteId}
              onChange={(e) => setCohorteId(e.target.value)}
              placeholder="ej. c-2026"
              className="w-full border rounded px-3 py-2 text-sm"
              data-testid="cohorte-id-input"
            />
          </div>
        </div>
      </section>

      {!hasContext && (
        <p className="text-sm text-gray-500 italic">
          Ingresá la materia y la cohorte para continuar.
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
