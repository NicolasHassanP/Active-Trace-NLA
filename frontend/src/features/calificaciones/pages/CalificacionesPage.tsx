/**
 * CalificacionesPage — orchestrates the calificaciones feature with tab navigation.
 *
 * Tabs:
 *   1. Importar      — upload + preview + activity selection + confirm (F1.1)
 *   2. Umbral        — configure approval threshold per materia (F2.1)
 *                      ADMIN → UmbralConfigDefault (scope global, sets default materia/cohorte)
 *                      PROFESOR/COORDINADOR → UmbralConfigDocente (scope propio, override)
 *   3. Ranking       — approved activities ranking table (F2.3)
 *   4. Reporte       — quick metrics for materia×cohorte (F2.4)
 *   5. Notas finales — grouped final grades, exportable (F2.5)
 *
 * Materia/cohorte context is entered once at the top and shared across all tabs.
 */
import { useState } from 'react'
import { useAuth } from '@/features/auth/hooks/useAuth'
import SelectorMateriaCohorte from '../components/SelectorMateriaCohorte'
import ImportarCalificacionesForm from '../components/ImportarCalificacionesForm'
import UmbralConfigDefault from '../components/UmbralConfigDefault'
import UmbralConfigDocente from '../components/UmbralConfigDocente'
import RankingTable from '../components/RankingTable'
import ReporteMateriaPanel from '../components/ReporteMateria'
import NotasFinalesTable from '../components/NotasFinalesTable'
import { PageHeader } from '@/shared/components/ui'

type Tab = 'importar' | 'umbral' | 'ranking' | 'reporte' | 'notas'

const TABS: { id: Tab; label: string }[] = [
  { id: 'importar', label: 'Importar' },
  { id: 'umbral', label: 'Umbral' },
  { id: 'ranking', label: 'Ranking' },
  { id: 'reporte', label: 'Reporte' },
  { id: 'notas', label: 'Notas finales' },
]

export default function CalificacionesPage() {
  const { roles } = useAuth()
  const [materiaId, setMateriaId] = useState('')
  const [cohorteId, setCohorteId] = useState('')
  const [activeTab, setActiveTab] = useState<Tab>('importar')

  const hasContext = materiaId.trim() !== '' && cohorteId.trim() !== ''
  const hasMateriaOnly = materiaId.trim() !== ''

  // ADMIN uses scope global → default component; others use override (docente) component
  const isAdmin = roles.includes('ADMIN')

  return (
    <div className="space-y-6">
      <PageHeader title="Calificaciones" />

      <SelectorMateriaCohorte
        materiaId={materiaId}
        cohorteId={cohorteId}
        onMateriaChange={setMateriaId}
        onCohorteChange={setCohorteId}
      />

      {!hasContext && (
        <p className="text-sm text-gray-500 italic">
          Ingresá la materia y la cohorte para continuar.
        </p>
      )}

      {hasContext && (
        <div className="space-y-4">
          {/* Tab bar */}
          <div className="flex gap-1 border-b">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 text-sm font-medium rounded-t border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-indigo-600 text-indigo-700 bg-indigo-50'
                    : 'border-transparent text-gray-600 hover:text-gray-800 hover:bg-gray-50'
                }`}
                data-testid={`tab-${tab.id}`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab panels */}
          <div className="pt-2">
            {activeTab === 'importar' && (
              <section className="space-y-3">
                <h2 className="text-lg font-semibold text-gray-700">Importar calificaciones</h2>
                <ImportarCalificacionesForm materia_id={materiaId} cohorte_id={cohorteId} />
              </section>
            )}

            {activeTab === 'umbral' && (
              <section className="space-y-3">
                <h2 className="text-lg font-semibold text-gray-700">
                  Umbral de aprobación
                </h2>
                {hasMateriaOnly ? (
                  isAdmin ? (
                    <UmbralConfigDefault
                      materia_id={materiaId}
                      cohorte_id={cohorteId || undefined}
                    />
                  ) : (
                    <UmbralConfigDocente materia_id={materiaId} />
                  )
                ) : (
                  <p className="text-sm text-gray-500 italic">Ingresá una materia para configurar el umbral.</p>
                )}
              </section>
            )}

            {activeTab === 'ranking' && (
              <section className="space-y-3">
                <h2 className="text-lg font-semibold text-gray-700">
                  Ranking de actividades aprobadas
                </h2>
                <RankingTable materia_id={materiaId} />
              </section>
            )}

            {activeTab === 'reporte' && (
              <section className="space-y-3">
                <h2 className="text-lg font-semibold text-gray-700">Reporte rápido</h2>
                <ReporteMateriaPanel materia_id={materiaId} cohorte_id={cohorteId} />
              </section>
            )}

            {activeTab === 'notas' && (
              <section className="space-y-3">
                <h2 className="text-lg font-semibold text-gray-700">Notas finales</h2>
                <NotasFinalesTable materia_id={materiaId} />
              </section>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
