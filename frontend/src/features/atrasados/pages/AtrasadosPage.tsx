/**
 * AtrasadosPage — reads materiaId/cohorteId from URL params (OQ-1).
 * Composes: ReporteMateriaHeader + AtrasadosFilters + AtrasadosTable + action to communicate.
 */
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAtrasados } from '../hooks/atrasadosHooks'
import { useReporteMateria } from '../hooks/atrasadosHooks'
import AtrasadosTable from '../components/AtrasadosTable'
import AtrasadosFilters from '../components/AtrasadosFilters'
import ReporteMateriaHeader from '../components/ReporteMateriaHeader'

export default function AtrasadosPage() {
  const { materiaId = '', cohorteId = '' } = useParams<{ materiaId: string; cohorteId: string }>()
  const navigate = useNavigate()

  const [selectedActividades, setSelectedActividades] = useState<string[]>([])
  const [selectedEmails, setSelectedEmails] = useState<Set<string>>(new Set())

  const atrasadosQuery = useAtrasados({
    materia_id: materiaId,
    cohorte_id: cohorteId,
    actividades: selectedActividades.length > 0 ? selectedActividades : undefined,
  })

  const reporteQuery = useReporteMateria(materiaId, cohorteId)
  const alumnos = atrasadosQuery.data ?? []

  function toggleSelect(email: string) {
    setSelectedEmails((prev) => {
      const next = new Set(prev)
      if (next.has(email)) next.delete(email)
      else next.add(email)
      return next
    })
  }

  function handleComunicar() {
    const emailsParam = Array.from(selectedEmails).join(',')
    navigate(`/comunicaciones?destinatarios=${encodeURIComponent(emailsParam)}&materia_id=${materiaId}&cohorte_id=${cohorteId}`)
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6 p-6">
      <h1 className="text-2xl font-bold text-gray-900">Alumnos atrasados</h1>

      <ReporteMateriaHeader
        reporte={reporteQuery.data}
        isLoading={reporteQuery.isLoading}
      />

      {atrasadosQuery.isLoading && (
        <div className="text-sm text-gray-500">Cargando alumnos…</div>
      )}

      {atrasadosQuery.isError && (
        <div role="alert" className="text-sm text-red-600">
          Error al cargar la lista de atrasados.
        </div>
      )}

      {!atrasadosQuery.isLoading && !atrasadosQuery.isError && (
        <>
          <AtrasadosFilters
            alumnos={alumnos}
            selectedActividades={selectedActividades}
            onChangeActividades={setSelectedActividades}
          />

          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">
              {selectedEmails.size > 0
                ? `${selectedEmails.size} alumno(s) seleccionado(s)`
                : 'Seleccioná alumnos para comunicar'}
            </p>
            <button
              onClick={handleComunicar}
              disabled={selectedEmails.size === 0}
              className="px-4 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-40"
              data-testid="comunicar-btn"
            >
              Comunicar a seleccionados
            </button>
          </div>

          <AtrasadosTable
            alumnos={alumnos}
            selectedEmails={selectedEmails}
            onToggleSelect={toggleSelect}
          />
        </>
      )}
    </div>
  )
}
